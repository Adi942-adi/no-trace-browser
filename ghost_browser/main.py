from __future__ import annotations

import signal
import sys
from typing import Sequence

from .cli import DEFAULT_TOR_PROXY, parse_args, parse_proxy_timeout, parse_window_size, resolve_proxy
from .diagnostics import ProxyDiagnosticResult, run_proxy_diagnostic
from .runtime import configure_chromium_environment
from .settings import (
    AppSettings,
    PROXY_MODE_CUSTOM,
    PROXY_MODE_TOR,
    SettingsStore,
)


def run(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    args = parse_args(args_list)

    try:
        _ = resolve_proxy(args)
        width, height = parse_window_size(args.window_size)
        proxy_timeout = parse_proxy_timeout(args.proxy_timeout)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    settings_store = SettingsStore()
    stored_settings = settings_store.load()
    effective_settings = _merge_settings(stored_settings, args)
    proxy_url = _proxy_url_for_settings(effective_settings)
    proxy_mode = effective_settings.proxy_mode

    from PyQt5.QtWidgets import QApplication, QMessageBox
    from .browser import BrowserWindow
    from .profile import EphemeralProfileManager

    qt_argv = [sys.argv[0], *args_list]
    app = QApplication(qt_argv)

    proxy_diagnostic: ProxyDiagnosticResult | None = None
    if proxy_url and not args.skip_proxy_check:
        checked, proxy_diagnostic = _run_proxy_preflight(
            proxy_url=proxy_url,
            timeout_seconds=proxy_timeout,
            strict=args.strict_proxy,
            QMessageBox=QMessageBox,
        )
        if not checked:
            return 2

    configure_chromium_environment(proxy_url)

    profile_manager = EphemeralProfileManager(base_dir=args.profile_root)
    app.aboutToQuit.connect(profile_manager.cleanup)
    profile = profile_manager.create_qt_profile(parent=app, user_agent=effective_settings.user_agent or None)
    ephemeral_download_dir = profile_manager.root_path / "ephemeral-downloads"
    ephemeral_download_dir.mkdir(parents=True, exist_ok=True)

    window = BrowserWindow(
        profile=profile,
        start_url=effective_settings.startup_url,
        default_download_dir=effective_settings.download_dir or None,
        download_mode=effective_settings.download_mode,
        ephemeral_download_dir=str(ephemeral_download_dir),
        settings=effective_settings,
        settings_store=settings_store,
        proxy_mode=proxy_mode,
        proxy_reachable=proxy_diagnostic.ok if proxy_diagnostic else None,
        tor_endpoint_reachable=proxy_diagnostic.ok if proxy_diagnostic and proxy_mode == PROXY_MODE_TOR else None,
    )
    window.resize(width, height)
    window.show()

    def _quit(*_args) -> None:
        app.quit()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, _quit)

    exit_code = app.exec_()
    profile_manager.cleanup()
    return exit_code


def _merge_settings(stored: AppSettings, args) -> AppSettings:
    effective = stored.normalized()

    if args.start_url:
        effective.startup_url = args.start_url
    if args.download_dir:
        effective.download_dir = args.download_dir
    if args.user_agent:
        effective.user_agent = args.user_agent
    if args.download_mode:
        effective.download_mode = args.download_mode

    if args.tor:
        effective.proxy_mode = PROXY_MODE_TOR
        effective.custom_proxy_url = ""
    elif args.proxy:
        effective.proxy_mode = PROXY_MODE_CUSTOM
        effective.custom_proxy_url = args.proxy

    return effective.normalized()


def _proxy_url_for_settings(settings: AppSettings) -> str | None:
    if settings.proxy_mode == PROXY_MODE_TOR:
        return DEFAULT_TOR_PROXY
    if settings.proxy_mode == PROXY_MODE_CUSTOM:
        return settings.custom_proxy_url or None
    return None


def _run_proxy_preflight(
    proxy_url: str,
    timeout_seconds: float,
    strict: bool,
    QMessageBox,
) -> tuple[bool, ProxyDiagnosticResult]:
    while True:
        try:
            diagnostic = run_proxy_diagnostic(proxy_url, timeout_seconds=timeout_seconds)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            message = QMessageBox()
            message.setIcon(QMessageBox.Warning)
            message.setWindowTitle("Proxy Configuration Error")
            message.setText("The proxy setting is not valid.")
            message.setInformativeText(str(exc))
            message.exec_()
            return False, ProxyDiagnosticResult(False, proxy_url, "", str(exc))

        if diagnostic.ok:
            print(diagnostic.message)
            return True, diagnostic

        label = "error" if strict else "warning"
        print(f"{label}: {diagnostic.message}", file=sys.stderr)

        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Proxy Connection Issue")
        dialog.setText("Could not reach the configured proxy endpoint.")
        dialog.setInformativeText(
            "Check that Tor/proxy is running, then retry.\n"
            f"Endpoint: {diagnostic.endpoint}\n\n"
            "Retry check or continue without a verified proxy."
        )
        retry_button = dialog.addButton("Retry Check", QMessageBox.ActionRole)
        if strict:
            exit_button = dialog.addButton("Exit", QMessageBox.RejectRole)
            dialog.exec_()
            if dialog.clickedButton() is retry_button:
                continue
            if dialog.clickedButton() is exit_button:
                return False, diagnostic
            return False, diagnostic

        continue_button = dialog.addButton("Continue Anyway", QMessageBox.AcceptRole)
        exit_button = dialog.addButton("Exit", QMessageBox.RejectRole)
        dialog.exec_()
        clicked = dialog.clickedButton()
        if clicked is retry_button:
            continue
        if clicked is continue_button:
            return True, diagnostic
        if clicked is exit_button:
            return False, diagnostic
        return False, diagnostic


if __name__ == "__main__":
    raise SystemExit(run())

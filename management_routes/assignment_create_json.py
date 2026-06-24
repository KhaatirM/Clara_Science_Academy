"""JSON helpers for SPA assignment creation forms posting to legacy endpoints."""

from __future__ import annotations

from flask import flash, jsonify, redirect, request


def create_form_wants_json() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "").lower()
    )


def json_create_ok(message: str, *, redirect_url: str | None = None):
    payload: dict = {"success": True, "message": message}
    if redirect_url:
        payload["redirect_url"] = redirect_url
    return jsonify(payload)


def json_create_err(message: str, status: int = 400):
    return jsonify({"success": False, "message": message}), status


def create_form_err(message: str, *, redirect_target: str | None = None, flash_category: str = "danger"):
    if create_form_wants_json():
        return json_create_err(message)
    flash(message, flash_category)
    return redirect(redirect_target or request.url)


def create_form_ok(message: str, *, redirect_url: str):
    if create_form_wants_json():
        return json_create_ok(message, redirect_url=redirect_url)
    flash(message, "success")
    return redirect(redirect_url)

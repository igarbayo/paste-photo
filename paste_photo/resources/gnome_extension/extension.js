// SPDX-FileCopyrightText: 2026 igarbayo
// SPDX-License-Identifier: MIT
//
// PastePhoto helper para GNOME Shell (45+).
//
// En Wayland las apps no pueden ver otras ventanas ni simular teclas. Esta extensión expone
// en el bus de sesión lo mínimo que necesita PastePhoto:
//   ListWindows() -> JSON [{id, title, pid, app_id, focus}]
//   ActiveWindow() -> id (0 si ninguna)
//   Activate(id)
//   SendKeys(spec)  -> SOLO combinaciones de pegado (ctrl+v, alt+v, ctrl+shift+v)
// Limitar SendKeys a atajos de pegado evita que otra app la use para teclear cualquier cosa.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const BUS_NAME = 'io.github.igarbayo.PastePhoto';
const OBJECT_PATH = '/io/github/igarbayo/PastePhoto';
const IFACE = `
<node>
  <interface name="io.github.igarbayo.PastePhoto">
    <method name="ListWindows"><arg type="s" direction="out" name="windows"/></method>
    <method name="ActiveWindow"><arg type="t" direction="out" name="id"/></method>
    <method name="Activate"><arg type="t" direction="in" name="id"/></method>
    <method name="SendKeys"><arg type="s" direction="in" name="spec"/></method>
  </interface>
</node>`;

const ALLOWED_KEYS = new Set(['ctrl+v', 'alt+v', 'ctrl+shift+v']);
const KEYVALS = {
    ctrl: Clutter.KEY_Control_L,
    alt: Clutter.KEY_Alt_L,
    shift: Clutter.KEY_Shift_L,
    v: Clutter.KEY_v,
};

class Helper {
    constructor() {
        const seat = Clutter.get_default_backend().get_default_seat();
        this._keyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
    }

    _windows() {
        return global.get_window_actors()
            .map(actor => actor.meta_window)
            .filter(w => w && w.get_window_type() === Meta.WindowType.NORMAL);
    }

    ListWindows() {
        return JSON.stringify(this._windows().map(w => ({
            id: w.get_id(),
            title: w.get_title() || '',
            pid: w.get_pid(),
            app_id: w.get_wm_class() || '',
            focus: w.has_focus(),
        })));
    }

    ActiveWindow() {
        const w = global.display.get_focus_window();
        return w ? w.get_id() : 0;
    }

    Activate(id) {
        const w = this._windows().find(win => win.get_id() === Number(id));
        if (w)
            Main.activateWindow(w);
    }

    SendKeys(spec) {
        const normalized = String(spec).toLowerCase().replace(/\s+/g, '');
        if (!ALLOWED_KEYS.has(normalized))
            throw new Error(`Combinación no permitida: ${spec}`);
        const keys = normalized.split('+').map(k => KEYVALS[k]);
        const now = () => GLib.get_monotonic_time();
        for (const key of keys)
            this._keyboard.notify_keyval(now(), key, Clutter.KeyState.PRESSED);
        for (const key of keys.reverse())
            this._keyboard.notify_keyval(now(), key, Clutter.KeyState.RELEASED);
    }
}

export default class PastePhotoExtension extends Extension {
    enable() {
        this._helper = new Helper();
        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this._helper);
        this._dbus.export(Gio.DBus.session, OBJECT_PATH);
        this._nameId = Gio.bus_own_name(Gio.BusType.SESSION, BUS_NAME,
            Gio.BusNameOwnerFlags.NONE, null, null, null);
    }

    disable() {
        if (this._nameId)
            Gio.bus_unown_name(this._nameId);
        this._dbus?.unexport();
        this._dbus = null;
        this._helper = null;
        this._nameId = 0;
    }
}

"""
Material U — Pixel clean UI for exteraGram.

A thin "switcher" plugin: it does NOT hand-draw a new UI (that would be brittle
and break on every app update). Instead it flips exteraGram's own appearance
flags towards a flat, Material-You-friendly look (no liquid glass / blur, clean
switches, optional system font) and ships a self-diagnostic that dumps the exact
config keys present on THIS device/version — so the modern keys (liquid glass,
Monet/dynamic colours, "islands") can be targeted precisely without ADB.

Config facts this relies on (from exteraSquad/exteraGram source,
com/exteragram/messenger/ExteraConfig.java):
  * all options live in SharedPreferences named "exteraconfig";
  * `ExteraConfig.preferences` is a public static SharedPreferences;
  * each option is a `public static` field whose name usually equals its pref key.
"""

# These modules are provided by the exteraGram runtime (Chaquopy) at runtime on the
# device. They do not exist on a desktop, so editors flag them as unresolved — that is
# expected and harmless; `# type: ignore` silences the warning.
from base_plugin import BasePlugin  # type: ignore
from hook_utils import find_class, get_static_private_field, set_static_private_field  # type: ignore
from android_utils import run_on_ui_thread, log  # type: ignore
from client_utils import get_last_fragment  # type: ignore
from ui.alert import AlertDialogBuilder  # type: ignore
from ui.settings import Header, Switch, Text, Divider  # type: ignore
from typing import Any, List

__id__ = "material_u"
__name__ = "Material U — Pixel clean UI"
__description__ = (
    "Прибирає liquid glass / блюр та вирівнює вигляд exteraGram під Material You "
    "(як на Google Pixel). Містить діагностику, що показує реальні ключі налаштувань "
    "твоєї версії."
)
__author__ = "Danylo"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.0.0"
__app_version__ = ">=11.0.0"
__sdk_version__ = ">=1.0.0"

EXTERA_CONFIG = "com.exteragram.messenger.ExteraConfig"

# Known boolean flags from the public source. Key == static field name.
# `clean_value` is what a flat Material-You look wants.
#   (None means "leave as-is" / handled elsewhere.)
KNOWN_BOOL_FLAGS = {
    "forceBlur": False,        # off => no glassy blur behind bars/menus
    "newSwitchStyle": True,    # Material-style switches
    "disableDividers": False,  # keep subtle dividers (Material groups use them)
    "useSystemFonts": True,    # Roboto / device (Pixel) font
    "squareFab": False,        # round FAB reads more Material
    "centerTitle": False,      # Material = start-aligned titles
}

# Heuristics for discovering MODERN keys that the public source predates.
# A discovered key whose name matches one of these substrings gets the paired
# value when "Apply preset" runs. Case-insensitive.
PRESET_HEURISTICS = [
    # (substring, desired_value, why)
    ("liquidglass", False, "liquid glass off"),
    ("glass", False, "glass effects off"),
    ("island", False, "settings islands off"),
    ("blur", False, "blur off"),
    ("monet", True, "Monet / dynamic colours on"),
    ("dynamiccolor", True, "dynamic colours on"),
    ("materialyou", True, "Material You on"),
]


class MaterialUPlugin(BasePlugin):

    # ------------------------------------------------------------------ config
    def _config_class(self):
        cls = find_class(EXTERA_CONFIG)
        if cls is None:
            self.logger.error("ExteraConfig class not found — wrong app/version?")
        return cls

    def _prefs(self):
        """Live SharedPreferences('exteraconfig') from the running app."""
        cls = self._config_class()
        if cls is None:
            return None
        try:
            return get_static_private_field(cls, "preferences")
        except Exception as e:  # noqa: BLE001
            self.logger.exception(f"reading ExteraConfig.preferences failed: {e}")
            return None

    def _all_entries(self) -> List[tuple]:
        """Return sorted (key, value) of every stored exteraGram option."""
        prefs = self._prefs()
        if prefs is None:
            return []
        out = []
        try:
            for entry in prefs.getAll().entrySet().toArray():
                out.append((str(entry.getKey()), entry.getValue()))
        except Exception as e:  # noqa: BLE001
            self.logger.exception(f"getAll() failed: {e}")
        out.sort(key=lambda kv: kv[0].lower())
        return out

    def _get_bool(self, key: str, default: bool = False) -> bool:
        prefs = self._prefs()
        if prefs is None:
            return default
        try:
            return bool(prefs.getBoolean(key, default))
        except Exception:  # noqa: BLE001
            return default

    def _put_bool(self, key: str, value: bool) -> bool:
        """Persist a boolean flag AND update the live static field + refresh UI."""
        cls = self._config_class()
        prefs = self._prefs()
        if cls is None or prefs is None:
            return False
        ok = True
        # 1) persist to disk so it survives restart and the app reads it on load
        try:
            prefs.edit().putBoolean(key, bool(value)).apply()
        except Exception as e:  # noqa: BLE001
            self.logger.exception(f"put '{key}' failed: {e}")
            ok = False
        # 2) update the in-memory static field so it takes effect without restart
        #    (ExteraConfig.loadConfig() is guarded and won't re-read once loaded)
        try:
            set_static_private_field(cls, key, bool(value))
        except Exception as e:  # noqa: BLE001
            # Field name may differ from pref key on newer versions — non-fatal.
            self.logger.warning(f"static field '{key}' not updated live: {e}")
        self._refresh_ui()
        return ok

    def _refresh_ui(self) -> None:
        """Best-effort: nudge the app to redraw. Some changes still need reopen."""
        try:
            from client_utils import get_notification_center  # type: ignore
            nc_cls = find_class("org.telegram.messenger.NotificationCenter")
            event = get_static_private_field(nc_cls, "mainUserInfoChanged")
            get_notification_center().postNotificationName(event, [])
        except Exception as e:  # noqa: BLE001
            self.logger.debug(f"UI refresh notification skipped: {e}")

    # --------------------------------------------------------------- lifecycle
    def on_plugin_load(self):
        # Dump the real keys once at load so they're also in the plugin log.
        try:
            entries = self._all_entries()
            self.logger.info(f"Material U: {len(entries)} exteraGram keys discovered")
            for k, v in entries:
                self.logger.info(f"  {k} = {v!r}")
        except Exception as e:  # noqa: BLE001
            self.logger.exception(f"startup dump failed: {e}")

    # ----------------------------------------------------------------- actions
    def _apply_preset(self, *_):
        changed = []
        # 1) known flags from source
        for key, want in KNOWN_BOOL_FLAGS.items():
            if want is None:
                continue
            if self._get_bool(key, want) != want:
                if self._put_bool(key, want):
                    changed.append(f"{key} -> {want}")
        # 2) modern keys discovered on THIS device, matched by heuristic
        for key, value in self._all_entries():
            if not isinstance(value, bool):
                continue
            lk = key.lower()
            for sub, want, _why in PRESET_HEURISTICS:
                if sub in lk and value != want:
                    if self._put_bool(key, want):
                        changed.append(f"{key} -> {want}")
                    break
        self._toast_result(changed)

    def _toast_result(self, changed: List[str]):
        if changed:
            msg = "Застосовано Material You:\n\n• " + "\n• ".join(changed)
            msg += "\n\nДеякі зміни видно після повторного відкриття екрана або перезапуску exteraGram."
        else:
            msg = ("Нічого не змінено — усе вже у чистому стані, або ключі твоєї версії "
                   "не збіглися з евристикою. Відкрий «Показати всі ключі» і надішли список "
                   "розробнику, щоб додати точні назви.")
        self._show_dialog("Material U", msg)

    def _show_keys(self, *_):
        entries = self._all_entries()
        if not entries:
            self._show_dialog("Material U", "Не вдалося прочитати налаштування exteraGram.")
            return
        lines = [f"{k} = {v!r}" for k, v in entries]
        body = f"Знайдено {len(entries)} ключів у exteraconfig:\n\n" + "\n".join(lines)
        self._show_dialog("Ключі exteraGram", body)

    def _copy_keys(self, *_):
        entries = self._all_entries()
        text = "\n".join(f"{k} = {v!r}" for k, v in entries)
        try:
            from android_utils import copy_to_clipboard  # type: ignore
            copy_to_clipboard(text)
        except Exception as e:  # noqa: BLE001
            self.logger.exception(f"clipboard failed: {e}")

    def _show_dialog(self, title: str, message: str):
        def _show():
            fragment = get_last_fragment()
            activity = fragment.getParentActivity() if fragment else None
            if not activity:
                log("Material U: no activity for dialog")
                return
            builder = AlertDialogBuilder(activity)
            builder.set_title(title)
            builder.set_message(message)
            builder.set_positive_button("OK", lambda b, which: b.dismiss())
            builder.show()
        run_on_ui_thread(_show)

    # ---------------------------------------------------------------- settings
    def _bool_changer(self, key: str):
        # returns an on_change(new_value) that writes straight to exteraGram config
        def _cb(new_value: bool):
            self._put_bool(key, bool(new_value))
        return _cb

    def create_settings(self) -> List[Any]:
        return [
            Header(text="Material You"),
            Text(
                text="✨ Застосувати пресет Material You",
                icon="msg_theme",
                on_click=self._apply_preset,
            ),
            Divider(text="Вимикає скло/блюр та вмикає Monet, де це підтримує твоя версія."),

            Header(text="Швидкі перемикачі"),
            Switch(
                key="mu_forceBlur",
                text="Примусовий блюр (liquid glass)",
                default=self._get_bool("forceBlur", False),
                icon="msg_photo_settings",
                on_change=self._bool_changer("forceBlur"),
            ),
            Switch(
                key="mu_newSwitchStyle",
                text="Material-стиль перемикачів",
                default=self._get_bool("newSwitchStyle", True),
                icon="msg_settings",
                on_change=self._bool_changer("newSwitchStyle"),
            ),
            Switch(
                key="mu_useSystemFonts",
                text="Системний шрифт (Roboto / Pixel)",
                default=self._get_bool("useSystemFonts", True),
                icon="msg_language",
                on_change=self._bool_changer("useSystemFonts"),
            ),
            Switch(
                key="mu_squareFab",
                text="Квадратна кнопка (FAB)",
                default=self._get_bool("squareFab", True),
                icon="msg_edit",
                on_change=self._bool_changer("squareFab"),
            ),
            Divider(),

            Header(text="Діагностика (знайти точні ключі)"),
            Text(
                text="🔍 Показати всі ключі exteraGram",
                icon="msg_info",
                on_click=self._show_keys,
            ),
            Text(
                text="📋 Скопіювати ключі в буфер",
                icon="msg_copy",
                on_click=self._copy_keys,
            ),
            Divider(text="Надішли цей список, щоб додати точні назви liquid glass / островців / Monet."),
        ]

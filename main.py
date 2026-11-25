import glob
import json
import os
import arabic_reshaper

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

# ===== تهیه کننده =====
CREATOR = "حافظ الیاس سالارزهی"
# ======================


def fa(text):
    text = text.replace(" - ", "، ")
    return arabic_reshaper.reshape(text)[::-1]


def find_font():
    paths = glob.glob("/system/fonts/*Naskh*.ttf")
    paths += glob.glob("/system/fonts/*Arab*.ttf")
    paths += glob.glob("/system/fonts/*Arab*.otf")
    return paths[0] if paths else None


FONT = find_font()
FONT_NAME = FONT or "Roboto"

DEFAULT_BOOKS = [
    "ریاض الصالحین - امام نووی",
    "صحیح بخاری - امام بخاری",
    "صحیح مسلم - امام مسلم",
    "سنن ابی داود - ابوداود",
    "جامع ترمذی - امام ترمذی",
]

THEMES = {
    "dark": {
        "bg": (0.06, 0.08, 0.11, 1),
        "banner": (0.09, 0.30, 0.26, 1),
        "banner_text": (0.97, 0.85, 0.50, 1),
        "banner_sub": (0.85, 0.92, 0.90, 1),
        "input_bg": (0.15, 0.19, 0.25, 1),
        "input_text": (1, 1, 1, 1),
        "hint": (0.6, 0.65, 0.7, 1),
        "book": (0.12, 0.40, 0.34, 1),
        "add": (0.85, 0.65, 0.20, 1),
        "toggle": (0.25, 0.30, 0.38, 1),
        "delete": (0.65, 0.20, 0.20, 1),
        "confirm": (0.95, 0.30, 0.10, 1),
        "footer": (0.65, 0.70, 0.75, 1),
        "btn_text": (1, 1, 1, 1),
    },
    "light": {
        "bg": (0.97, 0.95, 0.90, 1),
        "banner": (0.12, 0.45, 0.38, 1),
        "banner_text": (1, 0.92, 0.65, 1),
        "banner_sub": (0.92, 0.97, 0.95, 1),
        "input_bg": (1, 1, 1, 1),
        "input_text": (0.1, 0.1, 0.1, 1),
        "hint": (0.5, 0.5, 0.5, 1),
        "book": (0.15, 0.55, 0.45, 1),
        "add": (0.85, 0.60, 0.15, 1),
        "toggle": (0.60, 0.65, 0.70, 1),
        "delete": (0.75, 0.30, 0.30, 1),
        "confirm": (0.90, 0.25, 0.10, 1),
        "footer": (0.35, 0.40, 0.45, 1),
        "btn_text": (1, 1, 1, 1),
    },
}


def open_pdf(path):
    from jnius import autoclass

    activity = None
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
    except Exception:
        pass
    if activity is None:
        try:
            from android import mActivity
            activity = mActivity
        except Exception:
            pass
    if activity is None:
        raise RuntimeError("Android activity not found")

    StrictMode = autoclass("android.os.StrictMode")
    VmBuilder = autoclass("android.os.StrictMode$VmPolicy$Builder")
    StrictMode.setVmPolicy(VmBuilder().build())

    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    File = autoclass("java.io.File")

    intent = Intent(Intent.ACTION_VIEW)
    intent.setDataAndType(Uri.fromFile(File(path)), "application/pdf")
    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK |
                    Intent.FLAG_GRANT_READ_URI_PERMISSION)
    activity.startActivity(intent)


class RoundButton(Button):
    def __init__(self, bg=(1, 1, 1, 1), radius=18, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            self._c = Color(*bg)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[radius])
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *args):
        self._r.pos = self.pos
        self._r.size = self.size

    def set_bg(self, bg):
        self._c.rgba = bg


class Card(BoxLayout):
    def __init__(self, bg=(0, 0, 0, 1), radius=24, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._c = Color(*bg)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[radius])
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *args):
        self._r.pos = self.pos
        self._r.size = self.size

    def set_bg(self, bg):
        self._c.rgba = bg


class Library(BoxLayout):
    def __init__(self, data_dir, **kwargs):
        super().__init__(orientation="vertical", padding=14, spacing=12, **kwargs)
        self.data_file = os.path.join(data_dir, "books.json")
        self.files_file = os.path.join(data_dir, "files.json")
        self.theme_file = os.path.join(data_dir, "theme.txt")
        self.books = self.load_books()
        self.files = self.load_files()
        self.mode = self.load_mode()
        self.pending = None

        # ---- بنر بالا ----
        self.banner = Card(orientation="vertical", size_hint_y=0.17,
                           padding=10, spacing=2)
        self.bismillah = Label(text=fa("بسم الله الرحمن الرحیم"),
                               font_name=FONT_NAME, font_size=24,
                               size_hint_y=0.3)
        self.title = Label(text=fa("کتابخانه مکتب نور"),
                           font_name=FONT_NAME, font_size=40,
                           size_hint_y=0.45)
        self.subtitle = Label(text=fa("گنجینه کتاب های اهل سنت"),
                              font_name=FONT_NAME, font_size=22,
                              size_hint_y=0.25)
        self.banner.add_widget(self.bismillah)
        self.banner.add_widget(self.title)
        self.banner.add_widget(self.subtitle)
        self.add_widget(self.banner)

        # ---- جستجو ----
        self.search = TextInput(hint_text=fa("جستجو..."), font_name=FONT_NAME,
                                font_size=30, halign="right",
                                multiline=False, size_hint_y=0.07)
        self.search.bind(text=self.on_search)
        self.add_widget(self.search)

        # ---- افزودن کتاب ----
        row = BoxLayout(size_hint_y=0.07, spacing=8)
        self.name_input = TextInput(hint_text=fa("اسم کتاب"), font_name=FONT_NAME,
                                    font_size=26, halign="right", multiline=False)
        self.author_input = TextInput(hint_text=fa("نویسنده"), font_name=FONT_NAME,
                                      font_size=26, halign="right", multiline=False)
        self.add_btn = RoundButton(text=fa("افزودن"), font_name=FONT_NAME,
                                   font_size=26, size_hint_x=0.4)
        self.add_btn.bind(on_release=self.add_book)
        row.add_widget(self.add_btn)
        row.add_widget(self.author_input)
        row.add_widget(self.name_input)
        self.add_widget(row)

        self.inputs = [self.search, self.name_input, self.author_input]

        # ---- لیست کتاب ها ----
        self.scroll = ScrollView()
        self.list_box = BoxLayout(orientation="vertical",
                                  size_hint_y=None, spacing=10)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        self.add_widget(self.scroll)

        # ---- پایین صفحه ----
        footer = BoxLayout(size_hint_y=0.07, spacing=8)
        self.toggle_btn = RoundButton(font_name=FONT_NAME, font_size=22,
                                      size_hint_x=0.3)
        self.toggle_btn.bind(on_release=self.toggle_theme)
        self.footer_label = Label(text=fa("تهیه کننده: " + CREATOR),
                                  font_name=FONT_NAME, font_size=24)
        footer.add_widget(self.toggle_btn)
        footer.add_widget(self.footer_label)
        self.add_widget(footer)

        self.apply_theme()

    # ---------- ذخیره و خواندن ----------
    def load_books(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, encoding="utf-8") as f:
                return json.load(f)
        return list(DEFAULT_BOOKS)

    def save_books(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.books, f, ensure_ascii=False)

    def load_files(self):
        if os.path.exists(self.files_file):
            with open(self.files_file, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_files(self):
        with open(self.files_file, "w", encoding="utf-8") as f:
            json.dump(self.files, f, ensure_ascii=False)

    def load_mode(self):
        if os.path.exists(self.theme_file):
            with open(self.theme_file) as f:
                m = f.read().strip()
                if m in THEMES:
                    return m
        return "dark"

    # ---------- پنجره ها ----------
    def message(self, text, persian=False):
        content = BoxLayout(orientation="vertical", padding=12, spacing=12)
        lbl = Label(text=fa(text) if persian else text,
                    font_name=FONT_NAME if persian else "Roboto",
                    font_size=26 if persian else 18,
                    text_size=(Window.width * 0.8, None),
                    halign="center")
        ok = Button(text="OK", size_hint_y=0.25, font_size=24)
        content.add_widget(lbl)
        content.add_widget(ok)
        pop = Popup(title="", content=content, size_hint=(0.92, 0.6),
                    separator_height=0)
        ok.bind(on_release=pop.dismiss)
        pop.open()

    def choose_file(self, name):
        start = "/storage/emulated/0"
        if not os.path.exists(start):
            start = os.path.expanduser("~")

        content = BoxLayout(orientation="vertical", spacing=8, padding=8)
        chooser = FileChooserListView(path=start, filters=["*.pdf", "*.PDF"])
        btns = BoxLayout(size_hint_y=0.12, spacing=8)
        ok = Button(text="Select", font_size=24)
        cancel = Button(text="Cancel", font_size=24)
        btns.add_widget(cancel)
        btns.add_widget(ok)
        content.add_widget(chooser)
        content.add_widget(btns)
        pop = Popup(title="Choose PDF", content=content, size_hint=(0.97, 0.9))

        def on_ok(inst):
            if chooser.selection:
                self.files[name] = chooser.selection[0]
                self.save_files()
                pop.dismiss()
                self.show_books(self.search.text)
        ok.bind(on_release=on_ok)
        cancel.bind(on_release=pop.dismiss)
        pop.open()

    # ---------- رفتار برنامه ----------
    def on_book(self, name):
        path = self.files.get(name)
        if not path:
            self.choose_file(name)
            return
        if not os.path.exists(path):
            self.message("فایل پیدا نشد، دوباره انتخابش کن", persian=True)
            return
        try:
            open_pdf(path)
        except Exception as e:
            self.message("Error: " + repr(e))

    def toggle_theme(self, instance):
        self.mode = "light" if self.mode == "dark" else "dark"
        with open(self.theme_file, "w") as f:
            f.write(self.mode)
        self.apply_theme()

    def apply_theme(self):
        t = THEMES[self.mode]
        Window.clearcolor = t["bg"]
        self.banner.set_bg(t["banner"])
        self.bismillah.color = t["banner_text"]
        self.title.color = t["banner_text"]
        self.subtitle.color = t["banner_sub"]
        for ti in self.inputs:
            ti.background_normal = ""
            ti.background_active = ""
            ti.background_color = t["input_bg"]
            ti.foreground_color = t["input_text"]
            ti.hint_text_color = t["hint"]
            ti.cursor_color = t["banner_text"]
        self.add_btn.set_bg(t["add"])
        self.add_btn.color = t["btn_text"]
        self.toggle_btn.set_bg(t["toggle"])
        self.toggle_btn.color = t["btn_text"]
        self.toggle_btn.text = fa("حالت روز") if self.mode == "dark" else fa("حالت شب")
        self.footer_label.color = t["footer"]
        self.show_books(self.search.text)

    def add_book(self, instance):
        name = self.name_input.text.strip()
        author = self.author_input.text.strip()
        if not name:
            return
        self.books.append(name + " - " + author if author else name)
        self.save_books()
        self.name_input.text = ""
        self.author_input.text = ""
        self.show_books(self.search.text)

    def on_delete(self, index):
        if self.pending == index:
            name = self.books[index]
            del self.books[index]
            self.save_books()
            if name in self.files:
                del self.files[name]
                self.save_files()
            self.pending = None
        else:
            self.pending = index
            Clock.schedule_once(lambda dt: self.reset_pending(index), 3)
        self.show_books(self.search.text)

    def reset_pending(self, index):
        if self.pending == index:
            self.pending = None
            self.show_books(self.search.text)

    def show_books(self, q):
        t = THEMES[self.mode]
        self.list_box.clear_widgets()
        for i, b in enumerate(self.books):
            if q in b:
                row = BoxLayout(size_hint_y=None, height=120, spacing=8)

                asking = (self.pending == i)
                del_btn = RoundButton(
                    bg=t["confirm"] if asking else t["delete"],
                    text=fa("مطمئنی؟") if asking else fa("حذف"),
                    font_name=FONT_NAME, font_size=24, size_hint_x=0.2,
                    color=t["btn_text"])
                del_btn.bind(on_release=lambda inst, idx=i: self.on_delete(idx))

                has_file = b in self.files
                file_btn = RoundButton(
                    bg=t["toggle"],
                    text=fa("تغییر فایل") if has_file else fa("انتخاب فایل"),
                    font_name=FONT_NAME, font_size=20, size_hint_x=0.22,
                    color=t["btn_text"])
                file_btn.bind(on_release=lambda inst, n=b: self.choose_file(n))

                book_btn = RoundButton(
                    bg=t["book"], text=fa(b), font_name=FONT_NAME,
                    font_size=28, color=t["btn_text"])
                book_btn.bind(on_release=lambda inst, n=b: self.on_book(n))

                row.add_widget(del_btn)
                row.add_widget(file_btn)
                row.add_widget(book_btn)
                self.list_box.add_widget(row)

    def on_search(self, instance, value):
        self.pending = None
        self.show_books(value)


class MyApp(App):
    def build(self):
        os.makedirs(self.user_data_dir, exist_ok=True)
        return Library(self.user_data_dir)


MyApp().run()

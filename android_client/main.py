import os
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput


class Root(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.api_url = TextInput(
            text=os.getenv("NANYIA_API_URL", "http://127.0.0.1:8000/chat"),
            size_hint_y=0.14,
            multiline=False,
        )
        self.input_box = TextInput(hint_text="Pergunte para NanyIA", size_hint_y=0.2)
        self.output_box = TextInput(readonly=True)
        self.send_btn = Button(text="Enviar", size_hint_y=0.12)
        self.send_btn.bind(on_press=self.send)

        self.add_widget(self.api_url)
        self.add_widget(self.input_box)
        self.add_widget(self.send_btn)
        self.add_widget(self.output_box)

    def send(self, *_):
        msg = self.input_box.text.strip()
        if not msg:
            return

        url = self.api_url.text.strip()
        try:
            r = requests.post(url, json={"message": msg}, timeout=30)
            data = r.json()
            self.output_box.text = data.get("reply", str(data))
        except Exception as exc:
            self.output_box.text = f"Erro: {exc}"


class NanyIAApp(App):
    def build(self):
        return Root()


if __name__ == "__main__":
    NanyIAApp().run()

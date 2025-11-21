from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFillRoundFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.pickers import MDTimePicker
from kivy.core.window import Window

KV = '''
MDScreen:
    md_bg_color: app.theme_cls.bg_dark

    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)
        size_hint_y: None
        height: self.minimum_height
        pos_hint: {'center_x': .5, 'center_y': .5}

        MDLabel:
            text: "YTDownloader Mobile"
            halign: "center"
            theme_text_color: "Primary"
            font_style: "H4"

        MDTextField:
            id: url_field
            hint_text: "Enter Video URL"
            helper_text: "e.g. https://youtube.com/watch?v=..."
            helper_text_mode: "on_focus"
            icon_right: "link"
            mode: "rectangle"

        MDBoxLayout:
            orientation: 'horizontal'
            spacing: dp(10)
            size_hint_y: None
            height: dp(48)

            MDFillRoundFlatButton:
                text: "Download Now"
                pos_hint: {'center_y': .5}
                size_hint_x: 0.5
                on_release: app.download_video()

            MDFillRoundFlatButton:
                text: "Schedule"
                pos_hint: {'center_y': .5}
                size_hint_x: 0.5
                on_release: app.show_time_picker()

        MDLabel:
            id: status_label
            text: "Ready"
            halign: "center"
            theme_text_color: "Secondary"

class YTDownloaderApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        return Builder.load_string(KV)

    def download_video(self):
        url = self.root.ids.url_field.text
        if not url:
            self.root.ids.status_label.text = "Please enter a URL"
            return

        self.root.ids.status_label.text = f"Processing: {url}..."
        # Note: Actual download logic would be shared with backend/downloader.py

    def show_time_picker(self):
        time_dialog = MDTimePicker()
        time_dialog.bind(time=self.get_time)
        time_dialog.open()

    def get_time(self, instance, time):
        self.root.ids.status_label.text = f"Scheduled for {time}"

if __name__ == "__main__":
    YTDownloaderApp().run()

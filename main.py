from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from datetime import datetime


#Passando o gerenciador
class MeuGerenciador(ScreenManager):
    pass


#Tela inicial
class TelaInicio(Screen):
    def nada():
        return


#Tela de gerar serviços
class GerarServico(Screen):
    def nada():
        return


GUI = Builder.load_file('tela.kv')
class MeuAplicativo(App):
    def build(self):
        return GUI


    def fechar_aplicativo(self):
        App.get_running_app().stop()


MeuAplicativo().run()
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from datetime import datetime
import sqlite3


#Setando o banco de dados(o própio aplicativo cria o arquivo caso ele não exista)
#Tabela de clientes
con = sqlite3.connect("app.db")
cursor = con.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes (
    nome TEXT NOT NULL,
    telefone TEXT
)
""")
#Tabela de ordem de serviços
cursor.execute("""
CREATE TABLE IF NOT EXISTS ordens_servico (
    tipo TEXT,
    endereco TEXT,
    data TEXT,
    telefone TEXT,
    pago TEXT,
    descricao TEXT
)
""")


#Passando o gerenciador
class MeuGerenciador(ScreenManager):
    pass


#Função para cadastrar um novo cliente no banco de dados
def cadastrar_cliente(nome, telefone, email):
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute(
        "INSERT INTO clientes (nome, telefone) VALUES (?, ?)",
        (nome, telefone)
    )
    con.commit()
    con.close()


#Tela inicial
class TelaInicio(Screen):
    def nada():
        return


#Tela de gerar serviços
class CadastroCliente(Screen):
    def nada():
        return


class GerarServico(Screen):
    def nada():
        return


#Configuração de inicio do aplicativo
GUI = Builder.load_file('tela.kv')
class MeuAplicativo(App):
    def build(self):
        return GUI

    #Fechar o aplicativo ao pressionar a tecla de voltar do android
    def fechar_aplicativo(self):
        App.get_running_app().stop()


MeuAplicativo().run()
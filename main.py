from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from datetime import datetime
from kivymd.app import MDApp
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
import sqlite3
import locale


#Setando o banco de dados(o própio aplicativo cria o arquivo caso ele não exista)
def iniciar_banco():
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    #Tabela de clientes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        nome TEXT NOT NULL,
        telefone TEXT
    )
    """)
    #Tabela de ordens de serviço
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        tipo TEXT,
        endereco TEXT,
        data TEXT,
        telefone TEXT,
        pago TEXT,
        descricao TEXT
    )
    """)
    con.commit()
    con.close()


#Passando o gerenciador
class MeuGerenciador(ScreenManager):
    pass


#Função para cadastrar um novo cliente no banco de dados
def cadastrar_cliente(nome, telefone):
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


#Tela de cadastro de clientes
class CadastroCliente(Screen):
    def nada():
        return


#Tela de abretura de serviço
class GerarServico(Screen):
    #Abre um calendário para selecionar a data do serviço
    def abrir_calendario(self):
        picker = MDDatePicker()
        picker.bind(on_save=self.salvar_data)
        picker.open()

    #Salva a data selecionada e abre o seletor de hora
    def salvar_data(self, instance, value, date_range):
        self.data_selecionada = value
        self.abrir_relogio()

    #Abre o seletor de hora para selecionar a hora do serviço
    def abrir_relogio(self):
        time_picker = MDTimePicker()
        time_picker.bind(on_save=self.salvar_hora)
        time_picker.open()

    #Salva a hora selecionada e exibe a data e hora completas no campo de texto
    def salvar_hora(self, instance, time):
        hora = time.hour
        minuto = time.minute
        if instance.am_pm == "pm" and hora < 12:
            hora += 12
        if instance.am_pm == "am" and hora == 12:
            hora = 0
        data_hora = datetime(
            self.data_selecionada.year,
            self.data_selecionada.month,
            self.data_selecionada.day,
            hora,
            minuto)
        self.ids.data_servico.text = data_hora.strftime("%d/%m/%Y %H:%M")


#Configuração de inicio do aplicativo
class MeuAplicativo(MDApp):
    def build(self):
        iniciar_banco()
        self.theme_cls.locale = "pt_BR"
        #Carregando o arquivo KV responsável pela interface
        return Builder.load_file('tela.kv')

    #Fechar o aplicativo ao pressionar a tecla de voltar do android
    def fechar_aplicativo(self):
        self.stop()

#Rodando o aplicativo
MeuAplicativo().run()
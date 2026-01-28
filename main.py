from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.app import MDApp
from kivymd.uix.pickers import MDTimePicker
from datetime import datetime
import sqlite3
from kivy.uix.button import Button
import calendar

# ------------------ Banco de Dados ------------------ #
def iniciar_banco():
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            nome TEXT NOT NULL,
            telefone TEXT
        )
    """)
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

def cadastrar_cliente(nome, telefone):
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute(
        "INSERT INTO clientes (nome, telefone) VALUES (?, ?)",
        (nome, telefone)
    )
    con.commit()
    con.close()

#gerenciador de telas
class MeuGerenciador(ScreenManager):
    pass

#Tala Inicial
class TelaInicio(Screen):
    pass

#Tela Cadastro de Cliente
class CadastroCliente(Screen):
    pass

#Tela Gerar Serviço com calendário personalizado
class GerarServico(Screen):
    def abrir_calendario(self):
        # Cria BoxLayout do calendário
        self.cal_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.cal_box.size_hint_y = None
        self.cal_box.height = 400
        self.ids.box_data.clear_widgets()
        self.ids.box_data.add_widget(self.cal_box)
        self.mes_atual = datetime.now().month
        self.ano_atual = datetime.now().year
        self.atualizar_calendario()
        # Cria BoxLayout do calendário
        self.cal_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.cal_box.size_hint_y = None
        self.cal_box.height = 400
        self.ids.box_data.clear_widgets()
        self.ids.box_data.add_widget(self.cal_box)
        self.mes_atual = datetime.now().month
        self.ano_atual = datetime.now().year
        self.atualizar_calendario()
    #Configuração do calendário
    def atualizar_calendario(self):
        self.cal_box.clear_widgets()
        nome_meses = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                      "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        # Título mês/ano
        titulo = BoxLayout(size_hint_y=None, height=40)
        lbl_mes = BoxLayout(size_hint_x=0.9)
        lbl_mes.add_widget(Button(text=f"{nome_meses[self.mes_atual-1]} {self.ano_atual}", disabled=True))
        titulo.add_widget(lbl_mes)
        self.cal_box.add_widget(titulo)
        # Grid dos dias
        grid = GridLayout(cols=7, spacing=2, padding=2, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for dia in ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]:
            grid.add_widget(Button(text=dia, size_hint_y=None, height=40, disabled=True))
        primeiro_dia, qtd_dias = calendar.monthrange(self.ano_atual, self.mes_atual)
        for _ in range(primeiro_dia):
            grid.add_widget(Button(text="", disabled=True))
        for d in range(1, qtd_dias+1):
            btn = Button(text=str(d), size_hint_y=None, height=40)
            btn.bind(on_release=self.selecionar_dia)
            grid.add_widget(btn)
        self.cal_box.add_widget(grid)
        # Botões de navegação horizontal do mês
        nav_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        btn_anterior = Button(text="Mês Anterior")
        btn_anterior.bind(on_release=self.mes_anterior)
        btn_proximo = Button(text="Próximo Mês")
        btn_proximo.bind(on_release=self.proximo_mes)
        nav_box.add_widget(btn_anterior)
        nav_box.add_widget(btn_proximo)
        self.cal_box.add_widget(nav_box)
    # Seleção do dia passando para o seletor de hora
    def selecionar_dia(self, instance):
        dia = int(instance.text)
        self.data_selecionada = datetime(self.ano_atual, self.mes_atual, dia)
        self.abrir_relogio()
    # Navegação entre meses
    def proximo_mes(self, instance):
        if self.mes_atual == 12:
            self.mes_atual = 1
            self.ano_atual += 1
        else:
            self.mes_atual += 1
        self.atualizar_calendario()
    # Navegação entre meses
    def mes_anterior(self, instance):
        if self.mes_atual == 1:
            self.mes_atual = 12
            self.ano_atual -= 1
        else:
            self.mes_atual -= 1
        self.atualizar_calendario()
    # Seletor de hora
    def abrir_relogio(self):
        time_picker = MDTimePicker()
        time_picker.bind(on_save=self.salvar_hora)
        time_picker.open()
    # Salvar hora selecionada
    def salvar_hora(self, instance, time):
        hora = time.hour
        minuto = time.minute
        data_hora = self.data_selecionada.replace(hour=hora, minute=minuto)
        self.ids.data_servico.text = data_hora.strftime("%d/%m/%Y %H:%M")
        # Fecha o calendário
        for widget in self.ids.widgets_gerar_servico.children:
            widget.opacity = 1
            widget.disabled = False
        if hasattr(self, 'cal_box') and self.cal_box:
            self.ids.box_data.clear_widgets()
            self.cal_box = None

#Configuração do aplicativo
class MeuAplicativo(MDApp):
    def build(self):
        iniciar_banco()
        self.theme_cls.primary_palette = "Blue"
        return Builder.load_file("tela.kv")
    #Fechar o aplicativo
    def fechar_aplicativo(self):
        self.stop()

# Execução do aplicativo
if __name__ == "__main__":
    MeuAplicativo().run()

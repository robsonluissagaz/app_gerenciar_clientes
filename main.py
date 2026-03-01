from time import time

from kivy.lang import Builder
from kivy.properties import NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.app import MDApp
from kivymd.uix.pickers import MDTimePicker
from datetime import datetime
import sqlite3
from kivy.uix.button import Button
import calendar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.list import ThreeLineListItem
from kivy.properties import StringProperty
from kivy.clock import Clock

# ------------------ Banco de Dados ------------------ #
def iniciar_banco():
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ordens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            nome_cliente TEXT,
            endereco TEXT,
            data DATETIME,
            telefone TEXT,
            pago TEXT,
            descricao TEXT,
            valor REAL
        )
    """)
    con.commit()
    con.close()

def salvar_ordem(tipo, nome, endereco, data, telefone, pago, descricao, valor):
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute("""
        INSERT INTO ordens (tipo, nome_cliente, endereco, data, telefone, pago, descricao, valor)
        VALUES (?,?, ?, ?, ?, ?, ?, ?)
    """, (
        tipo,
        nome,
        endereco,
        data,
        telefone,
        pago,
        descricao,
        float(valor) if valor else 0.0
    ))
    con.commit()
    con.close()

#gerenciador de telas
class MeuGerenciador(ScreenManager):
    pass

#Tala Inicial
class TelaInicio(Screen):
    def on_pre_enter(self):
        Clock.schedule_once(self.atualizar_faturamento)
    #Atualiza a label de faturamento do mês toda vez que a tela for exibida
    def atualizar_faturamento(self, *args):
        self.ids.faturamento_mes.text = \
            f"Faturamento do mês: R$ {self.carregar_faturamento_mes():.2f}"
    #Função para carregar o faturamento do mês atual somando os valores das ordens pagas
    def carregar_faturamento_mes(self):
        con = sqlite3.connect("app.db")
        cur = con.cursor()
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        data_comparacao = f'01/{mes_atual:02d}/{ano_atual}'
        data_comparacao1 = f'31/{mes_atual:02d}/{ano_atual}'
        cur.execute("""select SUM(valor) from ordens
                    where data >= ? and data <= ? and pago = 'SIM'""",
                    (data_comparacao, data_comparacao1))
        resultado = cur.fetchone()[0]
        con.close()
        return resultado if resultado else 0.0

#Tela Gerar Serviço com calendário personalizado
class GerarServico(Screen):
    valor = NumericProperty(0.0)
    #Função que salva a ordem no banco de dados
    def confirmar_servico(self):
        salvar_ordem(
            self.ids.tipo.text,
            self.ids.nome_cliente.text.strip().upper(),
            self.ids.endereco.text.strip().upper(),
            self.ids.data_servico.text,
            self.ids.numero_contato.text,
            'SIM' if self.ids.pago_switch.active else 'NÃO',
            self.ids.descricao.text.strip().upper(),
            self.valor if hasattr(self, "valor") else 0
        )
        self.limpar_campos()
        self.mostrar_popup_sucesso()
    #Função para mostrar o diálogo de confirmação
    def mostrar_popup_sucesso(self):
        conteudo = MDLabel(
            text="Ordem de serviço gerada com sucesso!",
            halign="center",
            theme_text_color="Custom",
            text_color=(0, 0.7, 0, 1),
        )
        self.dialog = MDDialog(
            title="Sucesso!",
            type="custom",
            content_cls=conteudo,
            buttons=[
                MDFlatButton(
                    text="OK",
                    text_color=(0, 0.6, 0, 1),
                    on_release=lambda x: self.fechar_popup()
                ),
            ],
        )
        self.dialog.open()
    #Função para fechar o diálogo de confirmação
    def fechar_popup(self):
        self.dialog.dismiss()
        self.manager.current = "tela_inicio"
    #Função para os widgets da tela de gerar serviço
    def limpar_campos(self):
        self.ids.tipo.text = "SELECIONE O TIPO"
        self.ids.endereco.text = ""
        self.ids.nome_cliente.text = ""
        self.ids.data_servico.text = ""
        self.ids.numero_contato.text = ""
        self.ids.descricao.text = ""
        self.ids.valor_cobrado.text = ""
        self.ids.pago_switch.active = False

#Tela do calandário
class TelaCalendario(Screen):
    def on_pre_enter(self):
        self.abrir_calendario()
    #Abrir calendário
    def abrir_calendario(self):
        # Cria BoxLayout do calendário
        self.cal_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.cal_box.size_hint_y = 800
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
        titulo = BoxLayout(size_hint_y=None, height=80)
        lbl_mes = BoxLayout(size_hint_x=0.9)
        lbl_mes.add_widget(Button(text=f"{nome_meses[self.mes_atual-1]} {self.ano_atual}",
                                  background_normal='', background_color=(0.0, 0.55, 0.8, 1)))
        titulo.add_widget(lbl_mes)
        self.cal_box.add_widget(titulo)
        # Grid dos dias
        grid = GridLayout(cols=7, spacing=2, padding=2, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for dia in ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]:
            grid.add_widget(Button(text=dia, size_hint_y=None, height=80,
                                   background_normal='', background_color=(0.0, 0.55, 0.8, 1)))
        primeiro_dia, qtd_dias = calendar.monthrange(self.ano_atual, self.mes_atual)
        for _ in range(primeiro_dia):
            grid.add_widget(Button(text="", disabled=True))
        for d in range(1, qtd_dias+1):
            btn = Button(text=str(d), size_hint_y=None, height=80, 
                         background_normal='', background_color=(0.0, 0.55, 0.8, 1))
            btn.bind(on_release=self.selecionar_dia)
            grid.add_widget(btn)
        self.cal_box.add_widget(grid)
        # Botões de navegação horizontal do mês
        nav_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=80, spacing=10)
        btn_anterior = Button(text="Mês Anterior")
        btn_anterior.bind(on_release=self.mes_anterior)
        btn_proximo = Button(text="Próximo Mês")
        btn_proximo.bind(on_release=self.proximo_mes)
        btn_cancelar = Button(text="CANCELAR",background_normal='', background_color=(1, 0, 0, 1))
        btn_cancelar.bind(on_release=lambda x: self.fecha_calendario())
        nav_box.add_widget(btn_anterior)
        nav_box.add_widget(btn_proximo)
        nav_box.add_widget(btn_cancelar)
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
    # Salvar hora selecionada e volta para tela gerar serviço
    def salvar_hora(self, instance, time):
        hora = time.hour
        minuto = time.minute
        data_hora = self.data_selecionada.replace(hour=hora, minute=minuto)
        tela = self.manager.get_screen("gerar_servico")
        tela.ids.data_servico.text = data_hora.strftime("%Y-%m-%d %H:%M")
        self.manager.current = "gerar_servico"
    #Fecha o calendário e volta para a tela de gerar serviço
    def fecha_calendario(self):
        self.manager.current = "gerar_servico"

#Tela para a interface de inserir o valor
class TelaValorCobrado(Screen):
    valor_centavos = 0
    #Atualiza o display do valor toda vez que a tela for exibida
    def on_pre_enter(self):
        self.atualizar_display_valor()
    #Função para atualizar o display do valor formatando em reais e centavos
    def atualizar_display_valor(self):
        reais = self.valor_centavos // 100
        centavos = self.valor_centavos % 100
        self.ids.valor_display.text = (
            f"R$ {reais:,}".replace(',', '.') + f",{centavos:02d}")
    #Função para adicionar dígitos ao valor em centavos, limitando a 8 dígitos (999.999,99)
    def adicionar_digito(self, digito):
        if self.valor_centavos > 99999999:
            return
        self.valor_centavos = self.valor_centavos * 10 + digito
        self.atualizar_display_valor()
    #Função para apagar o último dígito do valor em centavos
    def apagar_digito(self):
        self.valor_centavos //= 10
        self.atualizar_display_valor()
    #Função para limpar o valor em centavos
    def limpar_valor(self):
        self.valor_centavos = 0
        self.atualizar_display_valor()
    #Função para salvar o valor formatando em reais e centavos e passando para a tela de gerar serviço
    def salvar_valor(self):
        texto = self.ids.valor_display.text
        valor_float = float(texto.replace("R$", "").replace(".", "").replace(",", ".").strip())
        tela_gerar = self.manager.get_screen("gerar_servico")
        tela_gerar.valor = valor_float
        tela_gerar.ids.valor_cobrado.text = (f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.manager.current = "gerar_servico"

#Tela de serviços
class TelaServicosAtivos(Screen):
    def on_pre_enter(self):
        self.carregar_servicos()
    #Função para carregar os serviços do dia atual ou futuros.
    def carregar_servicos(self):
        dia_atual = datetime.now().strftime("%Y-%m-%d")
        self.ids.lista_servicos.clear_widgets()
        con = sqlite3.connect("app.db")
        cur = con.cursor()
        cur.execute("""
            SELECT id, nome_cliente, data, endereco, valor, pago
            FROM ordens
            where data >= ?
            ORDER BY id DESC
        """, (dia_atual,))
        dados = cur.fetchall()
        con.close()
        for id_ordem, nome, data, endereco, valor, pago in dados:
            status = "PAGAMENTO EFETUADO" if pago == "SIM" else "PAGAMENTO PENDENTE"
            item = ThreeLineListItem(
                text=f"{nome}",
                secondary_text=f"Data: {data} | Valor: R$ {valor}      Endereço: {endereco}",
                tertiary_text=status,
                on_release=lambda x, id_=id_ordem: self.abrir_detalhes(id_)
            )
            self.ids.lista_servicos.add_widget(item)
    #Função para abrir a tela de detalhes do serviço passando as informações da ordem selecionada
    def abrir_detalhes(self, id_ordem):
        con = sqlite3.connect("app.db")
        cur = con.cursor()
        cur.execute("""
            select * from ordens where id = ?
        """, (id_ordem,))
        dados = cur.fetchall()
        con.close()
        tela = self.manager.get_screen("tela_descricao_servicos_ativos")
        tela.id_ordem = str(f"ID: {dados[0][0]}\nTipo: {dados[0][1]}\nCliente: {dados[0][2]}\nEndereço: {dados[0][3]}\nData: {dados[0][4]}\nTelefone: {dados[0][5]}\nPago: {dados[0][6]}\nDescrição: {dados[0][7]}\nValor: R$ {dados[0][8]:.2f}")
        self.manager.current = "tela_descricao_servicos_ativos"

class TelaDescricaoServicoAtivo(Screen):
    id_ordem = StringProperty("")
    def on_pre_enter(self):
        pass
    
    def cancelar_servico(self):
        self.dialog_confirmar = MDDialog(
            title="Confirmar Cancelamento",
            text="Tem certeza que deseja cancelar este serviço?",
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog_confirmar.dismiss()
                ),
                MDFlatButton(
                    text="CONFIRMAR",
                    on_release=lambda x: self.executar_cancelamento()
                )
            ]
        )
        self.dialog_confirmar.open()

    def executar_cancelamento(self):
        # Fecha o popup de confirmação primeiro
        self.dialog_confirmar.dismiss()
        con = sqlite3.connect("app.db")
        cur = con.cursor()
        id_real = self.id_ordem.split("\n")[0].split(": ")[1]
        cur.execute("DELETE FROM ordens WHERE id = ?", (id_real,))
        con.commit()
        con.close()
        self.dialog_sucesso = MDDialog(
            title="Serviço Cancelado",
            text="O serviço foi cancelado com sucesso.",
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.fechar_sucesso()
                )
            ]
        )
        self.dialog_sucesso.open()
        self.manager.get_screen("tela_servicos_ativos").carregar_servicos()
        
    def fechar_sucesso(self):
        self.dialog_sucesso.dismiss()
        self.manager.current = "tela_servicos_ativos"

class TelaServicosFinalizados(Screen):
    def on_pre_enter(self):
        self.carregar_servicos()
    #Função para carregar os serviços do dia anterior ou anteriores.
    def carregar_servicos(self):
        dia_atual = datetime.now().strftime("%d/%m/%Y")
        self.ids.lista_servicos.clear_widgets()
        con = sqlite3.connect("app.db")
        cur = con.cursor()
        cur.execute("""
            SELECT id, nome_cliente, data, endereco, valor, pago
            FROM ordens
            where data < ?
            ORDER BY id DESC
        """, (dia_atual,))
        dados = cur.fetchall()
        print(dados)
        con.close()
        for id_ordem, nome, data, endereco, valor, pago in dados:
            status = "PAGAMENTO EFETUADO" if pago == "SIM" else "PAGAMENTO PENDENTE"
            item = ThreeLineListItem(
                text=f"{nome}",
                secondary_text=f"Data: {data} | Valor: R$ {valor}      Endereço: {endereco}",
                tertiary_text=status,
                on_release=lambda x, id_=id_ordem: self.abrir_detalhes(id_)
            )
            self.ids.lista_servicos.add_widget(item)


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

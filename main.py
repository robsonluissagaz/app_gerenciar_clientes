from functools import partial
from pathlib import Path
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.app import MDApp
from kivymd.uix.pickers import MDTimePicker
from datetime import datetime
import sqlite3
from kivy.uix.button import Button
import webbrowser
import urllib.parse
import calendar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.list import ThreeLineListItem, TwoLineListItem
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
import os
import requests

ANDROID_BRIDGE_OK = False
ANDROID_BRIDGE_ERROR = ""

if platform == "android":
    try:
        from android import activity
        from jnius import autoclass, PythonJavaClass, java_method
        ANDROID_BRIDGE_OK = True
    except Exception as erro:
        ANDROID_BRIDGE_ERROR = str(erro)
        Logger.exception("FatuService: falha ao importar Android/PyJNIus")

from cloudsync import CloudSync, CloudSyncError

# Verifica a plataforma e cria os caminhos dos arquivos locais.
if platform == "android":
    from android.storage import app_storage_path

    APP_STORAGE_PATH = app_storage_path()
    DB_PATH = os.path.join(APP_STORAGE_PATH, "banco.db")
    GOOGLE_STORE_PATH = os.path.join(APP_STORAGE_PATH, "google_config.json")
else:
    DB_PATH = "banco.db"
    GOOGLE_STORE_PATH = "google_config.json"

google_store = JsonStore(GOOGLE_STORE_PATH)

#Criando o banco de dados
def iniciar_banco():
    con = sqlite3.connect(DB_PATH)
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
            competencia DATETIME,
            descricao TEXT,
            valor REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT,
            endereco TEXT
        )
    """)
    con.commit()
    con.close()

#Função que salva uma ordem de serviço no banco de dados
def salvar_ordem(tipo, nome, endereco, data, telefone, pago, descricao, valor):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    data_datetime = datetime.strptime(data, "%d/%m/%Y %H:%M")
    competencia = data_datetime.replace(day=1).date()
    # Insere no banco
    cur.execute("""
        INSERT INTO ordens (tipo, nome_cliente, endereco, data, telefone, pago, competencia, descricao, valor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tipo,
        nome,
        endereco,
        data_datetime,
        telefone,
        pago,
        competencia,
        descricao,
        float(valor) if valor else 0.0
    ))
    con.commit()
    con.close()
    # Atualiza a tela de serviços
    app = MeuAplicativo.get_running_app()
    tela = app.root.get_screen("tela_servicos_ativos")
    tela.carregar_servicos()

def atualizar_servicos_mensais():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    data_comparacao = datetime.now().replace(day=1).date()
    cur.execute("""
        SELECT id, tipo, nome_cliente, endereco, data, telefone, pago, descricao, valor
        FROM ordens
        WHERE competencia = ?
    """, (data_comparacao,))
    dados = cur.fetchall()
    con.close()
    return dados

#gerenciador de telas
class MeuGerenciador(ScreenManager):
    pass

#Tala Inicial
class TelaInicio(Screen):
    def on_pre_enter(self):
        Clock.schedule_once(self.atualizar_faturamento)

    def on_pre_leave(self):
        tela_financas = self.manager.get_screen('tela_gerenciamento_financas')
        tela_financas.ids.data_inicio.text = ''
        tela_financas.ids.data_fim.text = ''
        tela_financas.ids.botao_faturamento.text = ''
        tela_financas.ids.botao_faturamento.opacity = 0

    #Atualiza a label de faturamento do mês toda vez que a tela for exibida
    def atualizar_faturamento(self, *args):
        self.ids.botao_faturamento.text = \
            f"Faturamento do mês atual:\n[color=#00FF00]R$ {self.carregar_faturamento_mes():.2f}[/color]"
        limpar_campos = self.manager.get_screen('gerar_servico')
        limpar_campos.ids.tipo.text = "SELECIONE O TIPO"
        limpar_campos.ids.endereco.text = ""
        limpar_campos.ids.nome_cliente.text = ""
        limpar_campos.ids.data_servico.text = ""
        limpar_campos.ids.numero_contato.text = ""
        limpar_campos.ids.descricao.text = ""
        limpar_campos.ids.valor_cobrado.text = ""
        limpar_campos.ids.pago_switch.active = False
        
    #Função para carregar o faturamento do mês atual somando os valores das ordens pagas
    def carregar_faturamento_mes(self):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        competencia = f"{ano_atual}-{mes_atual:02d}"
        data_comparacao = f"{competencia}-01"
        cur.execute(""" SELECT SUM(valor) FROM ordens
                    WHERE competencia = ?
                    AND pago = 'SIM' """,
                    (data_comparacao,))
        resultado = cur.fetchone()[0]
        con.close()
        return resultado if resultado else 0.0

class TelaCadastrarCliente(Screen):
    def on_pre_enter(self):
        self.ids.nome_cliente.text = ""
        self.ids.numero_contato.text = ""
        self.ids.endereco.text = ""
    def cadastrar_cliente(self):
        nome = self.ids.nome_cliente.text.strip().upper()
        telefone = self.ids.numero_contato.text.strip()
        endereco = self.ids.endereco.text.strip().upper()
        if not nome or not telefone or not endereco:
            self.dialog_erro = MDDialog(
                title="Campos obrigatórios",
                text="[color=ff0000]Preencha todos os campos do cliente.[/color]",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.dialog_erro.dismiss()
                    )
                ]
            )
            self.dialog_erro.open()
            return
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            INSERT INTO clientes (nome, telefone, endereco)
            VALUES (?, ?, ?)
        """, (nome, telefone, endereco))
        con.commit()
        con.close()
        self.dialog_sucesso = MDDialog(
            title="Cliente Cadastrado",
            text=f"Cliente {nome} cadastrado com sucesso!",
            md_bg_color=(0.95, 0.98, 0.95, 1),
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="OK",
                    md_bg_color=(0.2, 0.7, 0.3, 1),
                    on_release=lambda x: self.dialog_sucesso.dismiss()
                )
            ]
        )
        self.dialog_sucesso.open()
        self.ids.nome_cliente.text = ""
        self.ids.numero_contato.text = ""
        self.ids.endereco.text = ""

class TelaProcurarCliente(Screen):
    def on_pre_enter(self):
        self.ids.nome_cliente.text = ""
        self.ids.lista_clientes.clear_widgets()

    def buscar_cliente(self):
        nome_busca = self.ids.nome_cliente.text.strip().upper()
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT nome, telefone, endereco
            FROM clientes
            WHERE nome LIKE ?
            ORDER BY nome
        """, (f"%{nome_busca}%",))
        resultados = cur.fetchall()
        con.close()
        self.ids.lista_clientes.clear_widgets()
        if resultados:
            for nome, telefone, endereco in resultados:
                item = ThreeLineListItem(
                    text=nome,
                    secondary_text=f"Telefone: {telefone}",
                    tertiary_text=f"Endereço: {endereco}")
                item.bind(
                    on_release=partial(
                        self.selecionar_cliente,
                        nome,
                        telefone,
                        endereco))
                self.ids.lista_clientes.add_widget(item)
        else:
            self.dialog_erro = MDDialog(
                title="Cliente não encontrado",
                text="[color=ff0000]Nenhum cliente encontrado com esse nome.[/color]",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.dialog_erro.dismiss()
                        )])
            self.dialog_erro.open()

    def selecionar_cliente(self, nome, telefone, endereco, *args):
        tela_servico = self.manager.get_screen("gerar_servico")
        tela_servico.ids.nome_cliente.text = nome
        tela_servico.ids.numero_contato.text = telefone
        tela_servico.ids.endereco.text = endereco
        self.manager.current = "gerar_servico"

#Tela Gerar Serviço com calendário personalizado
class TelaGerarServico(Screen):
    def on_pre_enter(self):
        tela_calendario = self.manager.get_screen("tela_calendario")
        tela_calendario.tela_atual = "gerar_servico"
        tela_valor_cobrado = self.manager.get_screen("valor_servico")
        tela_valor_cobrado.tela_atual = "gerar_servico"
    valor = NumericProperty(0.0)
    #Função que salva a ordem no banco de dados
    def confirmar_servico(self):
        if (
            self.ids.tipo.text == "SELECIONE O TIPO" or
            not self.ids.descricao.text.strip() or
            not self.ids.data_servico.text or
            not self.ids.nome_cliente.text.strip() or
            not self.ids.numero_contato.text or
            not self.ids.endereco.text.strip() or
            not self.valor):
            self.dialog_erro = MDDialog(
                title="Campos obrigatórios",
                text="[color=ff0000]Preencha todos os campos[/color]",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.dialog_erro.dismiss()
                    )
                ]
            )
            self.dialog_erro.open()
            return
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
        app = MeuAplicativo.get_running_app()
        app.root.get_screen("tela_servicos_ativos").carregar_servicos()
        app.root.get_screen("tela_servicos_finalizados").carregar_servicos()
        app.root.get_screen("tela_servicos_nao_pagos").carregar_servicos()
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
    tela_atual = StringProperty("")
    widget_atual = StringProperty("")
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
        tela = self.manager.get_screen(self.tela_atual)
        if self.tela_atual != 'tela_gerenciamento_financas':
            tela.ids.data_servico.text = data_hora.strftime("%d/%m/%Y %H:%M")
        else:
            if self.widget_atual == 'data_inicio':
                tela.ids.data_inicio.text = data_hora.strftime("%d/%m/%Y %H:%M")
            else:
                tela.ids.data_fim.text = data_hora.strftime("%d/%m/%Y %H:%M")
        self.manager.current = self.tela_atual
    #Fecha o calendário e volta para a tela anterior
    def fecha_calendario(self):
        self.manager.current = self.tela_atual

#Tela para a interface de inserir o valor
class TelaValorCobrado(Screen):
    tela_atual = StringProperty("")
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
        tela_gerar = self.manager.get_screen(self.tela_atual)
        tela_gerar.valor = valor_float
        tela_gerar.ids.valor_cobrado.text = (f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.limpar_valor()
        self.manager.current = self.tela_atual
    #Função para o botão cancelar
    def cancelar(self):
        self.manager.current = self.tela_atual

#Tela de serviços
class TelaServicosAtivos(Screen):
    def on_pre_enter(self):
        tela = self.manager.get_screen('tela_descricao_servicos')
        tela.tela_anterior = 'tela_servicos_ativos'
    #Função para carregar os serviços do dia atual ou futuros.
    def carregar_servicos(self):
        dia_atual = datetime.now().strftime("%Y-%m-%d")
        self.ids.lista_servicos.clear_widgets()
        con = sqlite3.connect(DB_PATH)
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
            data = datetime.strptime(data, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            item = ThreeLineListItem(
                text=f"{nome}",
                secondary_text=f"Data: {data} | Valor: R$ {valor}      Endereço: {endereco}",
                tertiary_text=status,
                on_release=lambda x, id_=id_ordem: self.abrir_detalhes(id_)
            )
            self.ids.lista_servicos.add_widget(item)
    #Função para abrir a tela de detalhes do serviço passando as informações da ordem selecionada
    def abrir_detalhes(self, id_ordem):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            select * from ordens where id = ?
        """, (id_ordem,))
        dados = cur.fetchall()
        con.close()
        tela = self.manager.get_screen("tela_descricao_servicos")
        data_br = datetime.strptime(dados[0][4], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        tela.id_ordem = str(f"Tipo: {dados[0][1]}\n\nCliente: {dados[0][2]}\n\nEndereço: {dados[0][3]}\n\nData: {data_br}\n\nTelefone: {dados[0][5]}\nPago: {dados[0][6]}\nValor: R$ {dados[0][9]:.2f}\n\nDescrição: {dados[0][8]}")
        tela.id_real = str(id_ordem)
        self.manager.current = "tela_descricao_servicos"

class TelaDescricaoServicos(Screen):
    id_ordem = StringProperty("")
    id_real = StringProperty("")
    tela_anterior = StringProperty("")

    def on_pre_enter(self):
        tela_editar = self.manager.get_screen("editar_servico")
        tela_editar.id_real = self.id_real
        self.manager.get_screen(self.tela_anterior).carregar_servicos()

    def editar_servico(self):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            select * from ordens where id = ?
        """, (self.id_real,))
        dados = cur.fetchall()
        con.close()
        tela = self.manager.get_screen("editar_servico")
        tela.tela_anterior = 'tela_descricao_servicos'
        tela.ids.tipo.text = dados[0][1]
        tela.ids.nome_cliente.text = dados[0][2]
        tela.ids.endereco.text = dados[0][3]
        data = dados[0][4]
        tela.ids.data_servico.text = datetime.strptime(data, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        tela.ids.numero_contato.text = dados[0][5]
        tela.ids.pago_switch.active = True if dados[0][6] == "SIM" else False
        tela.ids.descricao.text = dados[0][8]
        tela.valor = dados[0][9]
        tela.ids.valor_cobrado.text = f"R$ {dados[0][9]:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.manager.current = "editar_servico"
    
    def cancelar_servico(self):
        self.dialog_confirmar = MDDialog(
            title="Confirmar Cancelamento",
            text="[color=ff0000]Tem certeza que deseja cancelar este serviço?[/color]",
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
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("DELETE FROM ordens WHERE id = ?", (self.id_real,))
        con.commit()
        con.close()
        self.dialog_sucesso = MDDialog(
            title="Serviço Cancelado",
            text="[color=00ff00]O serviço foi cancelado com sucesso.[/color]",
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.fechar_sucesso()
                )
            ]
        )
        self.dialog_sucesso.open()
        self.manager.get_screen(self.tela_anterior).carregar_servicos()

    #Função para fechar o popup de sucesso e voltar para a tela anterior
    def fechar_sucesso(self):
        self.dialog_sucesso.dismiss()
        self.manager.current = self.tela_anterior

    def voltar_tela(self):
        self.manager.current = self.tela_anterior
    
    def compartilhar_texto(self):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            select telefone from ordens where id = ?
        """, (self.id_real,))
        telefone = cur.fetchone()
        con.close()
        texto = self.id_ordem
        texto = texto.replace("Tipo:", "📋 *Tipo:*")
        texto = texto.replace("Cliente:", "👤 *Cliente:*")
        texto = texto.replace("Endereço:", "📍 *Endereço:*")
        texto = texto.replace("Data:", "📅 *Data:*")
        texto = texto.replace("Telefone:", "📞 *Telefone:*")
        texto = texto.replace("Pago:", "✅ *Pago:*")
        texto = texto.replace("Valor:", "💰 *Valor:*")
        texto = texto.replace("Descrição:", "📝 *Descrição:*")
        texto += "\n\n💳 *PIX:*"
        texto += "\n65694742000100"
        url = (f"https://api.whatsapp.com/send"f"?phone={telefone[0]}"f"&text={urllib.parse.quote(texto)}")
        webbrowser.open(url)

class TelaEditarServico(Screen):
    valor = NumericProperty(0.0)
    id_real = StringProperty("")
    tela_anterior = StringProperty("")
    def on_pre_enter(self):
        tela_calendario = self.manager.get_screen("tela_calendario")
        tela_calendario.tela_atual = "editar_servico"
        tela_valor_cobrado = self.manager.get_screen("valor_servico")
        tela_valor_cobrado.tela_atual = "editar_servico"

    #Função para salvar as alterações do serviço editado no banco de dados
    def salvar_alteracoes(self):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            UPDATE ordens
            SET tipo = ?, nome_cliente = ?, endereco = ?, data = ?, telefone = ?, pago = ?, descricao = ?, valor = ?
            WHERE id = ?
        """, (
            self.ids.tipo.text,
            self.ids.nome_cliente.text.strip().upper(),
            self.ids.endereco.text.strip().upper(),
            datetime.strptime(self.ids.data_servico.text, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S"),
            self.ids.numero_contato.text,
            'SIM' if self.ids.pago_switch.active else 'NÃO',
            self.ids.descricao.text.strip().upper(),
            self.valor if hasattr(self, "valor") else 0,
            self.id_real
        ))
        con.commit()
        con.close()
        self.mostrar_popup_sucesso()
    #Função para mostrar o diálogo de confirmação de alterações salvas
    def mostrar_popup_sucesso(self):
        conteudo = MDLabel(
            text="Alterações salvas com sucesso!",
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

    #Função para fechar o diálogo de confirmação e voltar para a tela anterior
    def fechar_popup(self):
        tela_descricao = self.manager.get_screen(self.tela_anterior)
        tela_alvo = tela_descricao.tela_anterior
        self.manager.get_screen(tela_alvo).abrir_detalhes(tela_descricao.id_real)
        self.dialog.dismiss()
        self.manager.current = self.tela_anterior

class TelaServicosFinalizados(Screen):
    def on_pre_enter(self):
        tela = self.manager.get_screen('tela_descricao_servicos')
        tela.tela_anterior = 'tela_servicos_finalizados'
    #Função para carregar os serviços do dia anterior ou anteriores.
    def carregar_servicos(self):
        dia_atual = datetime.now().strftime("%Y-%m-%d")
        self.ids.lista_servicos_finalizados.clear_widgets()
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT id, nome_cliente, data, endereco, valor, pago
            FROM ordens
            where data < ?
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
            self.ids.lista_servicos_finalizados.add_widget(item)
    
    def abrir_detalhes(self, id_ordem):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            select * from ordens where id = ?
        """, (id_ordem,))
        dados = cur.fetchall()
        con.close()
        tela = self.manager.get_screen("tela_descricao_servicos")
        data_br = datetime.strptime(dados[0][4], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        tela.id_ordem = str(f"Tipo: {dados[0][1]}\n\nCliente: {dados[0][2]}\n\nEndereço: {dados[0][3]}\n\nData: {data_br}\n\nTelefone: {dados[0][5]}\nPago: {dados[0][6]}\nValor: R$ {dados[0][9]:.2f}\n\nDescrição: {dados[0][8]}")
        tela.id_real = str(id_ordem)
        self.manager.current = "tela_descricao_servicos"

class TelaServicosNaoPagos(Screen):
    def on_pre_enter(self):
        #self.carregar_servicos()
        tela = self.manager.get_screen('tela_descricao_servicos')
        tela.tela_anterior = 'tela_servicos_nao_pagos'
    #Função para carregar os serviços do dia anterior ou anteriores.
    def carregar_servicos(self):
        dia_atual = datetime.now().strftime("%Y-%m-%d")
        self.ids.lista_servicos_nao_pagos.clear_widgets()
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT id, nome_cliente, data, endereco, valor, pago
            FROM ordens
            where data < ?
            and pago = 'NÃO'
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
            self.ids.lista_servicos_nao_pagos.add_widget(item)
    
    def abrir_detalhes(self, id_ordem):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            select * from ordens where id = ?
        """, (id_ordem,))
        dados = cur.fetchall()
        con.close()
        tela = self.manager.get_screen("tela_descricao_servicos")
        data_br = datetime.strptime(dados[0][4], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        tela.id_ordem = str(f"Tipo: {dados[0][1]}\n\nCliente: {dados[0][2]}\n\nEndereço: {dados[0][3]}\n\nData: {data_br}\n\nTelefone: {dados[0][5]}\nPago: {dados[0][6]}\nValor: R$ {dados[0][9]:.2f}\n\nDescrição: {dados[0][8]}")
        tela.id_real = str(id_ordem)
        self.manager.current = "tela_descricao_servicos"

class TelaGerenciadorDeFinancas(Screen):
    def on_pre_enter(self):
        tela_calendario = self.manager.get_screen("tela_calendario")
        tela_calendario.tela_atual = "tela_gerenciamento_financas"

    def mandar_id_widget1(self):
        tela_calendario = self.manager.get_screen("tela_calendario")
        tela_calendario.widget_atual = "data_inicio"
        self.manager.current = 'tela_calendario'
    
    def mandar_id_widget2(self):
        tela_calendario = self.manager.get_screen("tela_calendario")
        tela_calendario.widget_atual = "data_fim"
        self.manager.current = 'tela_calendario'

    def carregar_faturamento(self):
        tela = self.manager.get_screen('tela_gerenciamento_financas')
        data_inicio = tela.ids.data_inicio.text
        data_fim = tela.ids.data_fim.text
        if not data_inicio or not data_fim:
            return 0
        from datetime import datetime
        data_inicio = datetime.strptime(data_inicio, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        data_fim = datetime.strptime(data_fim, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT SUM(valor)
            FROM ordens
            WHERE data >= ?
            and data <=?
            AND pago = 'SIM'
        """, (data_inicio, data_fim))
        total = cur.fetchone()[0]
        con.close()
        tela.ids.botao_faturamento.opacity = 1
        tela.ids.botao_faturamento.text = f"Faturamento do período selecionado\n[color=#00FF00]R$ {total}[/color]"

class TelaGerarCobranca(Screen):
    def on_pre_enter(self):
        self.ids.nome_cliente.text = ""
        self.ids.lista_clientes.clear_widgets()
    
    def buscar_cliente(self):
        nome_busca = self.ids.nome_cliente.text.strip().upper()
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT nome, telefone, endereco
            FROM clientes
            WHERE nome LIKE ?
            ORDER BY nome
        """, (f"%{nome_busca}%",))
        resultados = cur.fetchall()
        con.close()
        self.ids.lista_clientes.clear_widgets()
        if resultados:
            for nome, telefone, endereco in resultados:
                item = ThreeLineListItem(
                    text=nome,
                    secondary_text=f"Telefone: {telefone}",
                    tertiary_text=f"Endereço: {endereco}")
                self.ids.lista_clientes.add_widget(item)
                item.bind(
                on_release=partial(
                    self.gerar_cobranca,
                    nome,
                    telefone,
                    endereco))
        else:
            self.dialog_erro = MDDialog(
                title="Cliente não encontrado",
                text="[color=ff0000]Nenhum cliente encontrado com esse nome.[/color]",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.dialog_erro.dismiss()
                        )])
            self.dialog_erro.open()

    def gerar_cobranca(self, nome, telefone, endereco, *args):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""select sum(valor) from ordens
                    where nome_cliente = ?
                    and pago = 'NÃO'""", (nome,))
        total = cur.fetchone()[0] or 0
        con.close()
        self.dialog_erro = MDDialog(
                title="Erro",
                text="[color=ff0000]Nenhum valor a ser cobrado para este cliente.[/color]",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.dialog_erro.dismiss())])
        if not total:
            self.dialog_erro.open()
            return
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""select data from ordens
                    where nome_cliente = ?
                    and pago = 'NÃO'
                    order by data asc""", (nome,))
        datas = cur.fetchall()
        con.close()
        dialog = MDDialog(
            title="Gerar cobrança",
            text=f"""Cliente: {nome}\n
Endereço: {endereco}\n
Telefone: {telefone}\n
Datas de serviços pendentes: {', '.join([datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M") for data in datas])}\n\n
Total a pagar: R$ {total:.2f}\n\n
Pix(CNPJ): 65694742000100
                    """,
            buttons=[
                MDFlatButton(
                    text="Enviar via WhatsApp",
                    on_release=lambda x: self.enviar_whatsapp(nome, telefone, endereco, datas, total)
                ),
                MDFlatButton(
                    text="Cancelar",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
    def enviar_whatsapp(self, nome, telefone, endereco, datas, total):
        datas_formatadas = "\n".join([
        datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        for data in datas])
        texto = f"""
*Cliente*:
*{nome}*

📍 *Endereço:*
{endereco}

📞 *Telefone:*
{telefone}

📅 *Datas de atendimento:*
{datas_formatadas}

💰 *Valor total:*
R$ {total:.2f}

💳 *PIX(CNPJ)*:
65694742000100
"""
        url = (f"https://api.whatsapp.com/send"f"?phone={telefone}"f"&text={urllib.parse.quote(texto)}")
        webbrowser.open(url)

if platform == "android" and ANDROID_BRIDGE_OK:
    class GoogleSuccessListener(PythonJavaClass):
        __javainterfaces__ = [
            "com/google/android/gms/tasks/OnSuccessListener"
        ]
        __javacontext__ = "app"

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method("(Ljava/lang/Object;)V")
        def onSuccess(self, resultado):
            self.callback(resultado)


    class GoogleFailureListener(PythonJavaClass):
        __javainterfaces__ = [
            "com/google/android/gms/tasks/OnFailureListener"
        ]
        __javacontext__ = "app"

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method("(Ljava/lang/Exception;)V")
        def onFailure(self, excecao):
            self.callback(excecao)

class TelaBackUp(Screen):
    GOOGLE_DRIVE_REQUEST_CODE = 9001
    GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"

    google_email = StringProperty("")
    google_conectado = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cloudsync = None
        self.backup_selecionado = None
        self.dialog = None
        self.google_access_token = None
        self.google_account = None
        self._google_auth_client = None
        self._google_activity = None
        self._google_success_listener = None
        self._google_failure_listener = None
        self._google_disconnect_success_listener = None
        self._google_disconnect_failure_listener = None
        self._google_restauracao_tentada = False
        self._google_conexao_silenciosa = False

    def on_pre_enter(self):
        try:
            if self.cloudsync is None:
                self.cloudsync = CloudSync(db_path=DB_PATH, max_backups=10)
            self.carregar_backups()

            # Tenta restaurar a autorização apenas uma vez por execução do app.
            if not self._google_restauracao_tentada:
                self._google_restauracao_tentada = True
                Clock.schedule_once(
                    lambda dt: self.restaurar_conexao_google(),
                    0.5,
                )

        except Exception as erro:
            Logger.exception("FatuService: falha ao iniciar o sistema de backup")
            self.mostrar_dialogo(
                titulo="Erro no backup",
                texto=f"[color=ff0000]Não foi possível iniciar o backup.\n\n{erro}[/color]",
            )

    def fazer_backup(self):
        try:
            caminho_backup = self.cloudsync.criar_backup_local()
            nome_backup = os.path.basename(caminho_backup)
            self.carregar_backups()
            self.mostrar_dialogo(
                titulo="Backup realizado",
                texto=(
                    "[color=00aa00]"
                    "O backup foi criado com sucesso."
                    "[/color]\n\n"
                    f"Arquivo:\n{nome_backup}"))
        except CloudSyncError as erro:
            self.mostrar_dialogo(
                titulo="Erro no backup",
                texto=f"[color=ff0000]{erro}[/color]")
        except Exception as erro:
            self.mostrar_dialogo(
                titulo="Erro inesperado",
                texto=(
                    "[color=ff0000]"
                    f"Não foi possível criar o backup.\n\n{erro}"
                    "[/color]"
                ))

    def carregar_backups(self):
        self.ids.lista_backups.clear_widgets()
        self.backup_selecionado = None
        try:
            backups = self.cloudsync.listar_backups()
        except Exception as erro:
            self.ids.label_status_backup.text = (
                f"[color=ff0000]Erro ao carregar backups: {erro}[/color]")
            return
        if not backups:
            self.ids.label_status_backup.text = (
                "Nenhum backup local encontrado.")
            return
        ultimo_backup = backups[0]
        self.ids.label_status_backup.text = (
            "Último backup:\n"
            f"[color=00aa00]{ultimo_backup['data_formatada']}[/color]")
        for backup in backups:
            item = TwoLineListItem(
                text=backup["nome"],
                secondary_text=(
                    f"{backup['data_formatada']} • "
                    f"{backup['tamanho_formatado']}"),
                on_release=partial(self.selecionar_backup,backup))
            self.ids.lista_backups.add_widget(item)

    def selecionar_backup(self, backup, item):
        self.backup_selecionado = backup
        self.dialog_opcoes = MDDialog(
            title="Opções do backup",
            text=(
                f"Arquivo:\n{backup['nome']}\n\n"
                f"Data:\n{backup['data_formatada']}\n\n"
                f"Tamanho:\n{backup['tamanho_formatado']}"),
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog_opcoes.dismiss()),
                MDFlatButton(
                    text="EXCLUIR",
                    text_color=(1, 0, 0, 1),
                    on_release=lambda x: self.abrir_confirmacao_exclusao()),
                MDFlatButton(
                    text="RESTAURAR",
                    text_color=(0, 0.5, 1, 1),
                    on_release=lambda x: self.abrir_confirmacao_restauracao())])
        self.dialog_opcoes.open()

    def restaurar_backup(self):
        self.dialog_confirmacao.dismiss()
        try:
            backup_seguranca = (
                self.cloudsync.restaurar_backup_local(
                    self.backup_selecionado["caminho"],
                    criar_backup_seguranca=True))
            iniciar_banco()
            app = MeuAplicativo.get_running_app()
            app.root.get_screen("tela_servicos_ativos").carregar_servicos()
            app.root.get_screen("tela_servicos_finalizados").carregar_servicos()
            app.root.get_screen("tela_servicos_nao_pagos").carregar_servicos()
            app.root.get_screen("tela_inicio").atualizar_faturamento()
            self.carregar_backups()
            mensagem = (
                "[color=00aa00]"
                "O backup foi restaurado com sucesso."
                "[/color]")
            if backup_seguranca:
                mensagem += (
                    "\n\nFoi criado um backup de segurança dos "
                    "dados anteriores:\n"
                    f"{os.path.basename(backup_seguranca)}")
            self.mostrar_dialogo(
                titulo="Restauração concluída",
                texto=mensagem)
        except CloudSyncError as erro:
            self.mostrar_dialogo(
                titulo="Erro na restauração",
                texto=f"[color=ff0000]{erro}[/color]")
        except Exception as erro:
            self.mostrar_dialogo(
                titulo="Erro inesperado",
                texto=(
                    "[color=ff0000]"
                    f"Não foi possível restaurar o backup.\n\n{erro}"
                    "[/color]"))

    def abrir_confirmacao_restauracao(self):
        self.dialog_opcoes.dismiss()
        if not self.backup_selecionado:
            return
        self.dialog_confirmacao = MDDialog(
            title="Confirmar restauração",
            text=(
                "[color=ff0000]"
                "A restauração substituirá os dados atuais do aplicativo."
                "[/color]\n\n"
                "Antes da restauração será criado automaticamente "
                "um backup de segurança.\n\n"
                f"Restaurar o arquivo:\n"
                f"{self.backup_selecionado['nome']}?"),
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog_confirmacao.dismiss()),
                MDFlatButton(
                    text="RESTAURAR",
                    text_color=(0, 0.5, 1, 1),
                    on_release=lambda x: self.restaurar_backup())])
        self.dialog_confirmacao.open()

    def abrir_confirmacao_exclusao(self):
        self.dialog_opcoes.dismiss()
        if not self.backup_selecionado:
            return
        self.dialog_confirmacao = MDDialog(
            title="Excluir backup",
            text=(
                "[color=ff0000]"
                "Esta ação não poderá ser desfeita."
                "[/color]\n\n"
                f"Excluir o backup:\n"
                f"{self.backup_selecionado['nome']}?"),
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog_confirmacao.dismiss()),
                MDFlatButton(
                    text="EXCLUIR",
                    text_color=(1, 0, 0, 1),
                    on_release=lambda x: self.excluir_backup())])
        self.dialog_confirmacao.open()

    def excluir_backup(self):
        self.dialog_confirmacao.dismiss()
        try:
            nome_backup = self.backup_selecionado["nome"]
            self.cloudsync.excluir_backup(self.backup_selecionado["caminho"])
            self.backup_selecionado = None
            self.carregar_backups()
            self.mostrar_dialogo(
                titulo="Backup excluído",
                texto=(
                    "[color=00aa00]"
                    "O backup foi excluído com sucesso."
                    "[/color]\n\n"
                    f"Arquivo:\n{nome_backup}"))
        except CloudSyncError as erro:
            self.mostrar_dialogo(
                titulo="Erro ao excluir",
                texto=f"[color=ff0000]{erro}[/color]")
        except Exception as erro:
            self.mostrar_dialogo(
                titulo="Erro inesperado",
                texto=(
                    "[color=ff0000]"
                    f"Não foi possível excluir o backup.\n\n{erro}"
                    "[/color]"))

    def mostrar_dialogo(self, titulo, texto):
        self.dialog = MDDialog(
            title=titulo,
            text=texto,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss())])
        self.dialog.open()

    def conectar_google_drive(self, selecionar_conta=True):
        self._google_conexao_silenciosa = not selecionar_conta

        if self.google_conectado:
            if not self._google_conexao_silenciosa:
                self.mostrar_dialogo(
                    titulo="Google Drive conectado",
                    texto=(
                        "O aplicativo já está conectado ao Google Drive.\n\n"
                        f"Conta:\n[b]{self.google_email or 'Conta Google'}[/b]\n\n"
                        "Para utilizar outra conta, desconecte a conta atual."
                    ),
                )
            self._google_conexao_silenciosa = False
            return

        if platform != "android":
            self.mostrar_dialogo(
                titulo="Google Drive",
                texto=(
                    "A autorização do Google Drive precisa ser testada "
                    "no aplicativo Android."
                ),
            )
            return

        if not ANDROID_BRIDGE_OK:
            self.mostrar_dialogo(
                titulo="Google Drive",
                texto=(
                    "[color=ff0000]A integração Android/PyJNIus não foi carregada."
                    f"\n\n{ANDROID_BRIDGE_ERROR}[/color]"
                ),
            )
            return

        try:
            try:
                activity.unbind(
                    on_activity_result=self._on_google_activity_result
                )
            except Exception:
                pass

            activity.bind(
                on_activity_result=self._on_google_activity_result
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            Identity = autoclass(
                "com.google.android.gms.auth.api.identity.Identity"
            )
            AuthorizationRequest = autoclass(
                "com.google.android.gms.auth.api.identity.AuthorizationRequest"
            )
            Scope = autoclass(
                "com.google.android.gms.common.api.Scope"
            )
            ArrayList = autoclass("java.util.ArrayList")

            self._google_activity = PythonActivity.mActivity
            self._google_auth_client = Identity.getAuthorizationClient(
                self._google_activity
            )

            escopos = ArrayList()
            escopos.add(Scope(self.GOOGLE_DRIVE_SCOPE))

            AuthorizationPrompt = autoclass(
                "com.google.android.gms.auth.api.identity.AuthorizationRequest$Prompt"
            )

            builder = (
                AuthorizationRequest.builder()
                .setRequestedScopes(escopos)
            )

            # A seleção de conta é exibida somente na conexão manual.
            if selecionar_conta:
                builder.setPrompt(AuthorizationPrompt.SELECT_ACCOUNT)

            solicitacao = builder.build()

            tarefa = self._google_auth_client.authorize(solicitacao)

            self._google_success_listener = GoogleSuccessListener(
                self._on_google_authorization_success
            )
            self._google_failure_listener = GoogleFailureListener(
                self._on_google_authorization_failure
            )

            tarefa.addOnSuccessListener(self._google_success_listener)
            tarefa.addOnFailureListener(self._google_failure_listener)

        except Exception as erro:
            Logger.exception(
                "FatuService: erro ao iniciar autorização do Google Drive"
            )
            self.mostrar_dialogo(
                titulo="Erro no Google Drive",
                texto=(
                    "[color=ff0000]"
                    "Não foi possível iniciar a autorização.\n\n"
                    f"{erro}"
                    "[/color]"
                ),
            )

    def _on_google_authorization_success(self, resultado):
        Clock.schedule_once(
            lambda dt, resultado_google=resultado:
                self._processar_resultado_google(resultado_google),
            0,
        )

    def _on_google_authorization_failure(self, excecao):
        try:
            mensagem = (
                str(excecao.getMessage())
                if excecao and excecao.getMessage()
                else str(excecao)
            )
        except Exception:
            mensagem = "Erro desconhecido durante a autorização."

        if self._google_conexao_silenciosa:
            Logger.warning(
                "FatuService: não foi possível restaurar silenciosamente "
                f"a autorização Google: {mensagem}"
            )
            self._google_conexao_silenciosa = False
            return

        Clock.schedule_once(
            lambda dt: self.mostrar_dialogo(
                titulo="Falha na autorização",
                texto=f"[color=ff0000]{mensagem}[/color]",
            ),
            0,
        )

    def _processar_resultado_google(self, resultado):
        try:
            if resultado.hasResolution():
                # Na restauração automática, nunca abre seletor ou consentimento.
                # O usuário poderá tocar em CONECTAR para fazer isso manualmente.
                if self._google_conexao_silenciosa:
                    self._google_conexao_silenciosa = False
                    return

                pending_intent = resultado.getPendingIntent()
                self._google_activity.startIntentSenderForResult(
                    pending_intent.getIntentSender(),
                    self.GOOGLE_DRIVE_REQUEST_CODE,
                    None,
                    0,
                    0,
                    0,
                )
                return

            self._salvar_token_google(resultado)

        except Exception as erro:
            Logger.exception(
                "FatuService: erro ao processar autorização do Google"
            )
            self.mostrar_dialogo(
                titulo="Erro na autorização",
                texto=f"[color=ff0000]{erro}[/color]",
            )

    def _on_google_activity_result(
        self,
        request_code,
        result_code,
        intent,
    ):
        if request_code != self.GOOGLE_DRIVE_REQUEST_CODE:
            return

        try:
            Activity = autoclass("android.app.Activity")

            Logger.info(
                "FatuService: retorno Google "
                f"request_code={request_code}, "
                f"result_code={result_code}, "
                f"intent={intent}"
            )

            if result_code != Activity.RESULT_OK or intent is None:
                Clock.schedule_once(
                    lambda dt: self.mostrar_dialogo(
                        titulo="Autorização cancelada",
                        texto=(
                            "A conexão com o Google Drive "
                            "não foi autorizada."
                        ),
                    ),
                    0,
                )
                return

            resultado = (
                self._google_auth_client
                .getAuthorizationResultFromIntent(intent)
            )

            Clock.schedule_once(
                lambda dt, resultado_google=resultado:
                    self._salvar_token_google(resultado_google),
                0,
            )

        except Exception as erro:
            Logger.exception(
                "FatuService: erro no resultado da autorização Google"
            )

            mensagem = str(erro)

            Clock.schedule_once(
                lambda dt, msg=mensagem: self.mostrar_dialogo(
                    titulo="Falha na autorização",
                    texto=(
                        "[color=ff0000]"
                        "Não foi possível concluir a conexão "
                        "com o Google Drive."
                        f"\n\n{msg}"
                        "[/color]"
                    ),
                ),
                0,
            )

    def _salvar_token_google(self, resultado):
        try:
            token = resultado.getAccessToken()

            if not token:
                self.mostrar_dialogo(
                    titulo="Falha na autorização",
                    texto=(
                        "[color=ff0000]"
                        "O Google não retornou um token de acesso."
                        "[/color]"
                    ),
                )
                return

            self.google_access_token = str(token)
            self.google_account = resultado.toGoogleSignInAccount()

            email = ""
            if self.google_account:
                email_java = self.google_account.getEmail()
                if email_java:
                    email = str(email_java)

            # A Identity Authorization API pode não preencher getEmail().
            # Nesse caso, consulta o usuário conectado pela API do Google Drive.
            if not email:
                email = self.obter_email_google_drive()

            # Se a consulta não funcionar durante uma restauração silenciosa,
            # mantém o e-mail que já estava salvo localmente.
            if not email and google_store.exists("google_drive"):
                dados_salvos = google_store.get("google_drive")
                email = dados_salvos.get("email", "")

            self.google_email = email
            self.google_conectado = True
            self.salvar_conta_google_localmente()

            if not self._google_conexao_silenciosa:
                self.mostrar_dialogo(
                    titulo="Google Drive conectado",
                    texto=(
                        "[color=00aa00]"
                        "Google Drive conectado com sucesso."
                        "[/color]\n\n"
                        f"Conta:\n{self.google_email or 'Conta Google conectada'}"
                    ),
                )

            self._google_conexao_silenciosa = False

        except Exception as erro:
            Logger.exception(
                "FatuService: erro ao salvar autorização do Google"
            )
            self.mostrar_dialogo(
                titulo="Erro na conexão",
                texto=(
                    "[color=ff0000]"
                    "A autorização foi concluída, mas não foi possível "
                    "salvar os dados da conta.\n\n"
                    f"{erro}"
                    "[/color]"
                ),
            )

    def obter_email_google_drive(self):
        """Obtém o e-mail da conta autorizada pela API do Google Drive."""
        if not self.google_access_token:
            return ""

        try:
            resposta = requests.get(
                "https://www.googleapis.com/drive/v3/about",
                headers={
                    "Authorization": f"Bearer {self.google_access_token}",
                },
                params={
                    "fields": "user(emailAddress,displayName)",
                },
                timeout=15,
            )
            resposta.raise_for_status()

            dados = resposta.json()
            usuario = dados.get("user", {})
            return str(usuario.get("emailAddress", "")).strip()

        except requests.RequestException as erro:
            Logger.warning(
                "FatuService: não foi possível consultar o e-mail "
                f"da conta Google Drive: {erro}"
            )
            return ""
        except (TypeError, ValueError) as erro:
            Logger.warning(
                "FatuService: resposta inválida ao consultar o e-mail "
                f"do Google Drive: {erro}"
            )
            return ""

    def salvar_conta_google_localmente(self):
        try:
            google_store.put(
                "google_drive",
                email=self.google_email,
            )
        except Exception:
            Logger.exception(
                "FatuService: erro ao salvar conta Google localmente"
            )

    def restaurar_conexao_google(self):
        try:
            if not google_store.exists("google_drive"):
                return

            dados = google_store.get("google_drive")
            self.google_email = dados.get("email", "")

            if platform == "android" and ANDROID_BRIDGE_OK:
                self.conectar_google_drive(selecionar_conta=False)

        except Exception:
            self._google_conexao_silenciosa = False
            Logger.exception(
                "FatuService: erro ao restaurar conexão Google"
            )

    def confirmar_desconexao_google(self):
        if not self.google_conectado:
            self.mostrar_dialogo(
                titulo="Google Drive",
                texto="Nenhuma conta do Google Drive está conectada.",
            )
            return

        self.dialog_desconectar_google = MDDialog(
            title="Desconectar Google Drive",
            text=(
                "Deseja desconectar esta conta?\n\n"
                f"[b]{self.google_email or 'Conta Google conectada'}[/b]\n\n"
                "Ao conectar novamente, será possível selecionar outra conta."
            ),
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda x: (
                        self.dialog_desconectar_google.dismiss()
                    ),
                ),
                MDFlatButton(
                    text="DESCONECTAR",
                    text_color=(1, 0, 0, 1),
                    on_release=lambda x: self.desconectar_google_drive(),
                ),
            ],
        )
        self.dialog_desconectar_google.open()

    def desconectar_google_drive(self):
        try:
            if hasattr(self, "dialog_desconectar_google"):
                self.dialog_desconectar_google.dismiss()

            self._finalizar_desconexao_google()

        except Exception as erro:
            Logger.exception(
                "FatuService: erro ao desconectar Google Drive localmente"
            )
            self.mostrar_dialogo(
                titulo="Erro ao desconectar",
                texto=(
                    "[color=ff0000]"
                    "Não foi possível desconectar a conta do Google Drive."
                    f"\n\n{erro}"
                    "[/color]"
                ),
            )

    def _on_google_disconnect_success(self, resultado):
        Clock.schedule_once(
            lambda dt: self._finalizar_desconexao_google(),
            0,
        )

    def _on_google_disconnect_failure(self, excecao):
        try:
            mensagem = (
                str(excecao.getMessage())
                if excecao and excecao.getMessage()
                else str(excecao)
            )
        except Exception:
            mensagem = "Erro desconhecido ao desconectar a conta."

        Clock.schedule_once(
            lambda dt: self.mostrar_dialogo(
                titulo="Erro ao desconectar",
                texto=f"[color=ff0000]{mensagem}[/color]",
            ),
            0,
        )

    def _finalizar_desconexao_google(self):
        try:
            if google_store.exists("google_drive"):
                google_store.delete("google_drive")
        except Exception:
            Logger.exception(
                "FatuService: erro ao apagar conta Google salva"
            )

        self._limpar_conexao_google()
        self.mostrar_dialogo(
            titulo="Google Drive desconectado",
            texto=(
                "[color=00aa00]"
                "A conta foi desconectada com sucesso."
                "[/color]\n\n"
                "Ao conectar novamente, você poderá selecionar outra conta."
            ),
        )

    def _limpar_conexao_google(self):
        self.google_access_token = None
        self.google_account = None
        self.google_email = ""
        self.google_conectado = False
        self._google_success_listener = None
        self._google_failure_listener = None
        self._google_disconnect_success_listener = None
        self._google_disconnect_failure_listener = None
        self._google_conexao_silenciosa = False

#Configuração do aplicativo
class MeuAplicativo(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        try:
            iniciar_banco()
            return Builder.load_file("tela.kv")
        except Exception:
            Logger.exception("FatuService: falha durante build()")
            raise

    def on_start(self):
        Clock.schedule_once(self.carregar_telas, 0.5)

    def carregar_telas(self, dt):
        try:
            self.root.get_screen("tela_servicos_ativos").carregar_servicos()
            self.root.get_screen("tela_servicos_finalizados").carregar_servicos()
            self.root.get_screen("tela_servicos_nao_pagos").carregar_servicos()
        except Exception:
            Logger.exception("FatuService: erro ao carregar as telas iniciais")

    #Fechar o aplicativo
    def fechar_aplicativo(self):
        self.stop()

# Execução do aplicativo
if __name__ == "__main__":
    MeuAplicativo().run()

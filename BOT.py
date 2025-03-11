import logging
import threading
import time
import os
import dotenv
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException,
    UnexpectedAlertPresentException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from CALL import solicitar_token_e_realizar_chamada
from flask import Flask, jsonify
from telegram_bot import notificar_telegram

# Configurar o logging
logging.basicConfig(
    filename='BOT.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Inicializar o Flask
app = Flask(__name__)

# Carregar variáveis de ambiente do arquivo .env
dotenv.load_dotenv()
origem = os.getenv('ORIGEM')
destino = os.getenv('DESTINO')
login_user = os.getenv('LOGIN_USER')
login_password = os.getenv('LOGIN_PASSWORD')

# Opções do Edge
edge_options = Options()
edge_options.add_experimental_option("detach", True)
servico = Service(EdgeChromiumDriverManager().install())


# Classe de manipulação do navegador para reuso de funções comuns
class NavegadorAutomacao:
    def __init__(self):
        self.navegador = webdriver.Edge(service=servico, options=edge_options)
        self.excecoes_consecutivas = 0

    def clicar_se_existir(self, xpath):
        """Clica no elemento se o XPath for encontrado."""
        try:
            self.navegador.find_element(By.XPATH, xpath).click()
            return True
        except NoSuchElementException:
            return False
        except UnexpectedAlertPresentException as e:
            alert = self.navegador.switch_to.alert
            logging.error(f"UnexpectedAlertPresentException: Alerta inesperado encontrado: {alert.text}")
            alert.accept()
            return False

    def reiniciar(self):
        """Reinicia o navegador e realiza o login no Assyst."""
        self.navegador.quit()
        self.navegador = webdriver.Edge(service=servico, options=edge_options)
        iniciar_assyst(self)

    def tratar_excecao(self, e):
        """Método para tratar exceções com um dicionário de exceções mapeadas."""
        # Dicionário que mapeia exceções para funções de tratamento
        excecao_map = {
            NoSuchElementException: self.tratar_no_such_element,
            ElementClickInterceptedException: self.tratar_element_click_intercepted,
            TimeoutException: self.tratar_timeout_exception,
            UnexpectedAlertPresentException: self.tratar_unexpected_alert,
            WebDriverException: self.tratar_webdriver_exception,
        }

        # Itera sobre o dicionário e aplica o tratamento adequado
        for excecao_tipo, funcao_tratamento in excecao_map.items():
            if isinstance(e, excecao_tipo):
                return funcao_tratamento(e)

        # Se não encontrar a exceção no mapa, loga o erro genérico
        logging.error(f"Erro inesperado: {str(e)}")
        return False  # Retorna False se não for uma exceção tratada

    # Funções de tratamento específicas para cada exceção
    def tratar_no_such_element(self, e):
        self.excecoes_consecutivas += 1
        logging.warning(f"NoSuchElementException: Tentativa {self.excecoes_consecutivas}/3.")
        if self.excecoes_consecutivas >= 3:
            logging.error("NoSuchElementException: Número máximo de exceções atingido. Reiniciando o navegador...")
            self.reiniciar()
        return True  # Continuar o loop de automação

    def tratar_element_click_intercepted(self, e):
        logging.warning("ElementClickInterceptedException: Elemento obstrutivo ainda presente.")
        return True  # Continuar o loop de automação

    def tratar_timeout_exception(self, e):
        logging.error("TimeoutException: Tempo limite excedido. Reiniciando o navegador...")
        self.reiniciar()
        return True  # Reiniciar o navegador e continuar o loop

    def tratar_unexpected_alert(self, e):
        alert = self.navegador.switch_to.alert
        logging.error(f"UnexpectedAlertPresentException: Alerta inesperado encontrado: {alert.text}")
        alert.accept()
        return True  # Continuar o loop de automação

    def tratar_webdriver_exception(self, e):
        logging.error("WebDriverException: Erro de rede ou conexão. Reiniciando o navegador...")
        self.reiniciar()
        return True  # Reiniciar o navegador e continuar o loop


# Função para iniciar o sistema Assyst
def iniciar_assyst(nav: NavegadorAutomacao):
    try:
        time.sleep(5)
        nav.navegador.get("https://servicedesk.trt20.jus.br/assystweb/application.do")

        # Fazer login no Assyst:
        time.sleep(14)
        nav.navegador.find_element(By.XPATH, '//*[@id="login-user"]').send_keys(login_user)
        nav.navegador.find_element(By.XPATH, '//*[@id="login-password"]').send_keys(login_password)
        nav.navegador.find_element(By.XPATH, '//*[@id="loginSubmit"]').click()

        # Navegar para o Monitor de eventos
        time.sleep(10)
        nav.navegador.find_element(By.XPATH, '//*[@id="dijit__TreeNode_11_label"]').click()
        time.sleep(2)
        nav.navegador.find_element(By.XPATH, '//*[@id="dijit__TreeNode_15_label"]').click()
        time.sleep(4)
        nav.navegador.find_element(By.XPATH, '//*[@id="dijit__TreeNode_21_label"]').click()

    except Exception as e:
        logging.error(f"Erro ao iniciar Assyst: {str(e)}")
        raise


# Função para realizar chamada com tentativa múltipla
def realizar_chamada(origem, destino, max_tentativas=3):
    """Tenta realizar a chamada até obter sucesso ou atingir o limite de tentativas."""
    tentativa = 1
    while tentativa <= max_tentativas:
        try:
            resultado_chamada = solicitar_token_e_realizar_chamada(origem, destino)
            if resultado_chamada and resultado_chamada.get("codigo") == "000":
                logging.info(f"Ligação realizada com sucesso: {resultado_chamada}")
                notificar_telegram()  # Notificar o grupo do Telegram
                break  # Sai do loop ao obter sucesso
            else:
                logging.error(f"Falha ao realizar a ligação: Tentativa {tentativa}/{max_tentativas}. Retorno: {resultado_chamada}")
        except Exception as e:
            logging.error(f"Erro ao realizar a chamada na tentativa {tentativa}/{max_tentativas}: {str(e)}")

        tentativa += 1
        time.sleep(120)  # Aguarda 120 segundos antes de tentar novamente

    if tentativa > max_tentativas:
        logging.error("Número máximo de tentativas para realizar a ligação atingido.")


# Endpoint para Health Check
@app.route('/status', methods=['GET'])
def check_status():
    return jsonify(status="1")


# Função para rodar o Selenium e Flask simultaneamente
def iniciar_automacao_e_api():
    navegador = NavegadorAutomacao()

    # Função interna de automação
    def automacao():
        while True:
            try:
                # Atualizar pelo botão refresh:
                time.sleep(5)
                WebDriverWait(navegador.navegador, 10).until(EC.invisibility_of_element_located((By.ID, "contentOverlay")))
                navegador.navegador.find_element(By.XPATH, '//*[@id="emRefresh_button"]/div[1]').click()
                navegador.excecoes_consecutivas = 0  # Resetar o contador de exceções

            except Exception as e:
                if not navegador.tratar_excecao(e):
                    # Se a exceção não for tratada, loga o erro
                    logging.error(f"Erro inesperado: {str(e)}")
                continue

            # Ações subsequentes
            time.sleep(3)
            if not navegador.clicar_se_existir('//*[@id="menuActions_label"]'):
                continue
            time.sleep(2)
            if not navegador.clicar_se_existir('//*[@id="menuActions_$DisplayOnceAction(USER_CALLBACK)_text"]'):
                continue
            time.sleep(4)
            if navegador.clicar_se_existir('//*[@id="ManageActionForm.btSave_label"]'):
                time.sleep(1)
                threading.Thread(target=realizar_chamada, args=(origem, destino)).start()
                continue
            time.sleep(5)
            navegador.navegador.find_element(By.XPATH, '//*[@id="dijit__TreeNode_22_label"]').click()

    # Iniciar automação em thread
    threading.Thread(target=automacao).start()
    # Rodar Flask
    app.run(host='0.0.0.0', port=5000)


# Execução principal
if __name__ == "__main__":
    iniciar_automacao_e_api()

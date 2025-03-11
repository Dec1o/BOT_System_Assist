import requests
import dotenv
import time
import os

# Carregar variáveis de ambiente do arquivo .env
dotenv.load_dotenv()

# Variável global para armazenar o token e seu tempo de expiração
token_info = {
    "access_token": None,
    "expira_em": 0
}

def solicitar_token():
    """Solicita e retorna um novo token de acesso."""
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    
    url_token = "https://api.directcallsoft.com/request_token"
    data_token = {
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    response_token = requests.post(url_token, data=data_token)
    
    if response_token.status_code == 200:
        token_json = response_token.json()
        token_info['access_token'] = token_json['access_token']
        # Assumindo que o token expira em 3600 segundos (1 hora)
        token_info['expira_em'] = time.time() + 3600
        return token_info['access_token']
    else:
        print(f"Falha ao solicitar token: {response_token.status_code}, {response_token.text}")
        return None

def obter_token_valido():
    """Obtém um token válido, solicitando um novo se o atual estiver expirado."""
    if not token_info['access_token'] or time.time() >= token_info['expira_em']:
        return solicitar_token()
    return token_info['access_token']

def solicitar_token_e_realizar_chamada(origem, destino, gravar='n'):
    access_token = obter_token_valido()
    
    if access_token:
        # Realizar chamada telefônica
        url_chamada = "https://api.directcallsoft.com/voz/call"
        data_chamada = {
            'origem': origem,
            'destino': destino,
            'access_token': access_token  
        }
        response_chamada = requests.post(url_chamada, data=data_chamada)

        if response_chamada.status_code == 200:
            return response_chamada.json()
        else:
            print(f"Falha ao realizar a chamada: {response_chamada.status_code}, {response_chamada.text}")
            return None
    else:
        print("Não foi possível obter um token válido.")
        return None
    
    
    
# Exemplo de chamada da função
origem = os.getenv('ORIGEM')
destino = os.getenv('DESTINO')

# Realizar chamada telefônica
resultado_chamada = solicitar_token_e_realizar_chamada(origem, destino)

if resultado_chamada:
    print(f"Chamada realizada com sucesso: {resultado_chamada}")
else:
    print("Falha ao realizar a chamada.")

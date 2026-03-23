#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oscar Tracker 2026 - Bolao Zacadentes
Monitora a BBC e envia atualizacoes no WhatsApp automaticamente.
"""

import os
import sys

# Forçar UTF-8 no Windows
os.environ['PYTHONUTF8'] = '1'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import json
import time
import re
import urllib.request
import ssl
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO
# ============================================================
BBC_URL = 'https://www.bbc.com/portuguese/live/cz6ez2g04q8t'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, 'oscar_state.json')
GRUPO_WHATSAPP = 'Zacadentes'
INTERVALO_CHECAGEM = 60  # segundos
CHROME_PROFILE_DIR = os.path.join(SCRIPT_DIR, 'whatsapp_chrome_profile')

# ============================================================
# DADOS DO BOLÃO
# ============================================================
PALPITES = {
    'Melhor Filme': {
        'O Agente Secreto': ['Vitor'],
        'Uma Batalha Após a Outra': ['Célia', 'Sofia', 'Anderson'],
        'Bugonia': [],
        'F1: O Filme': [],
        'Frankenstein': [],
        'Hamnet': [],
        'Pecadores': [],
        'Marty Supreme': [],
        'Valor Sentimental': ['Vinícius'],
        'Sonhos de Trem': [],
    },
    'Melhor Filme Internacional': {
        'O Agente Secreto': ['Vitor', 'Sofia', 'Vinícius', 'Anderson'],
        'Foi Apenas Um Acidente': [],
        'Valor Sentimental': ['Célia'],
        'Sirat': [],
        'A Voz de Hind Rajab': [],
    },
    'Melhor Ator': {
        'Timothée Chalamet': [],
        'Ethan Hawke': [],
        'Wagner Moura': ['Vitor', 'Célia'],
        'Michael B. Jordan': ['Sofia', 'Vinícius', 'Anderson'],
        'Leonardo DiCaprio': [],
    },
    'Melhor Atriz': {
        'Jessie Buckley': ['Vitor', 'Célia', 'Sofia', 'Vinícius', 'Anderson'],
        'Rose Byrne': [],
        'Kate Hudson': [],
        'Renate Reinsve': [],
        'Emma Stone': [],
    },
    'Melhor Direção': {
        'Chloé Zhao': [],
        'Josh Safdie': [],
        'Paul Thomas Anderson': ['Vitor', 'Célia', 'Sofia', 'Anderson'],
        'Joachim Trier': [],
        'Ryan Coogler': ['Vinícius'],
    },
    'Melhor Ator Coadjuvante': {
        'Benício Del Toro': [],
        'Jacob Elordi': [],
        'Sean Penn': ['Sofia'],
        'Delroy Lindo': ['Vitor'],
        'Stellan Skarsgård': ['Célia', 'Vinícius', 'Anderson'],
    },
    'Melhor Atriz Coadjuvante': {
        'Elle Fanning': ['Vitor'],
        'Inga Ibsdotter Lilleaas': [],
        'Teyana Taylor': ['Célia'],
        'Wunmi Mosaku': ['Vinícius'],
        'Amy Madigan': ['Sofia', 'Anderson'],
    },
    'Melhor Roteiro Original': {
        'Blue Moon': [],
        'Foi Apenas Um Acidente': [],
        'Marty Supreme': [],
        'Valor Sentimental': ['Vitor'],
        'Pecadores': ['Célia', 'Sofia', 'Vinícius', 'Anderson'],
    },
    'Melhor Roteiro Adaptado': {
        'Bugonia': [],
        'Frankenstein': [],
        'Hamnet': ['Vitor', 'Célia', 'Vinícius'],
        'Uma Batalha Após a Outra': ['Sofia', 'Anderson'],
        'Sonhos de Trem': [],
    },
    'Melhor Direção de Elenco': {
        'Hamnet': [],
        'Marty Supreme': [],
        'Uma Batalha Após a Outra': [],
        'O Agente Secreto': ['Vitor', 'Célia'],
        'Pecadores': ['Sofia', 'Vinícius', 'Anderson'],
    },
    'Melhor Animação': {
        'Guerreiras do K-Pop': ['Vitor', 'Célia', 'Sofia', 'Vinícius', 'Anderson'],
        'Zootopia 2': [],
        'Elio': [],
        'Arco': [],
        'A Pequena Amélie': [],
    },
    'Melhor Fotografia': {
        'Marty Supreme': [],
        'Frankenstein': ['Vitor'],
        'Pecadores': ['Sofia', 'Anderson'],
        'Uma Batalha Após a Outra': [],
        'Sonhos de Trem': ['Célia', 'Vinícius'],
    },
}

# Padrões para detectar categorias (mais específicos primeiro!)
CATEGORY_PATTERNS = [
    ('Melhor Filme Internacional', [r'filme internacional', r'filme estrangeiro']),
    ('Melhor Atriz Coadjuvante', [r'atriz coadjuvante']),
    ('Melhor Ator Coadjuvante', [r'ator coadjuvante']),
    ('Melhor Roteiro Original', [r'roteiro original']),
    ('Melhor Roteiro Adaptado', [r'roteiro adaptado']),
    ('Melhor Direção de Elenco', [r'dire[çc][ãa]o de elenco', r'casting']),
    ('Melhor Fotografia', [r'fotografia', r'cinematografia']),
    ('Melhor Animação', [r'melhor.*anima[çc][ãa]o', r'longa.*anima[çc][ãa]o', r'anima[çc][ãa]o.*ano']),
    ('Melhor Direção', [r'melhor dire[çc][ãa]o\b', r'\bmelhor diretor\b']),
    ('Melhor Ator', [r'\bmelhor ator\b', r'\bator principal\b']),
    ('Melhor Atriz', [r'\bmelhor atriz\b', r'\batriz principal\b']),
    ('Melhor Filme', [r'\bmelhor filme\b', r'\bfilme do ano\b']),
]


# ============================================================
# FUNÇÕES DE ESTADO
# ============================================================

def load_state():
    """Carrega o estado salvo"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'seen_urns': [],
        'placar': {
            'Anderson': 2,
            'Sofia': 2,
            'Célia': 1,
            'Vitor': 1,
            'Vinícius': 1,
        },
        'categorias_anunciadas': [],
    }


def save_state(state):
    """Salva o estado"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ============================================================
# FUNÇÕES BBC
# ============================================================

def fetch_bbc_results():
    """Busca os resultados do live blog da BBC"""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(BBC_URL, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    html = resp.read().decode('utf-8')

    # Extrair JSON do __NEXT_DATA__
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        # Fallback
        scripts = re.findall(r'<script[^>]*>\s*(\{"props".*?)\s*</script>', html, re.DOTALL)
        if not scripts:
            return []
        data_str = scripts[0]
    else:
        data_str = match.group(1)

    data = json.loads(data_str)
    results = data['props']['pageProps']['pageData']['liveTextStream']['content']['data']['results']
    return results


def extract_text_from_blocks(block):
    """Extrai texto recursivamente dos blocos da BBC"""
    texts = []
    if isinstance(block, dict):
        if 'text' in block and isinstance(block['text'], str):
            t = block['text'].strip()
            if t:
                texts.append(t)
        for v in block.values():
            texts.extend(extract_text_from_blocks(v))
    elif isinstance(block, list):
        for item in block:
            texts.extend(extract_text_from_blocks(item))
    return texts


def get_header_text(result):
    """Extrai o título/header de um resultado"""
    header_texts = extract_text_from_blocks(result.get('header', {}))
    # Pega o primeiro texto único (evita duplicatas nos blocos)
    seen = set()
    unique = []
    for t in header_texts:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[0] if unique else ''


def get_urn(result):
    """Extrai o URN único do resultado"""
    return result.get('urn', '')


def get_timestamp(result):
    """Extrai o timestamp de publicação"""
    dates = result.get('dates', {})
    return dates.get('firstPublished', '')


# ============================================================
# FUNÇÕES DE DETECÇÃO
# ============================================================

def is_winner_announcement(title):
    """Verifica se o título anuncia um vencedor"""
    title_lower = title.lower()
    # Keywords simples
    keywords = ['ganha', 'ganhou', 'vence', 'venceu', 'vencedor', 'vencedora']
    if any(kw in title_lower for kw in keywords):
        return True
    # Padrões regex mais flexíveis (ex: "leva o terceiro Oscar")
    patterns = [r'leva.*oscar', r'leva.*pr[eê]mio', r'conquista.*oscar', r'conquista.*pr[eê]mio']
    return any(re.search(p, title_lower) for p in patterns)


def detect_category(title):
    """Detecta a categoria do Oscar a partir do título"""
    title_lower = title.lower()

    # Excluir categorias de curtas (não estão no bolão)
    if 'curta' in title_lower:
        return None

    for category, patterns in CATEGORY_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, title_lower):
                return category
    return None


def find_winner_name(category, title):
    """Encontra o nome do vencedor no título baseado nos candidatos do bolão"""
    if category not in PALPITES:
        return None

    title_lower = title.lower()

    # Palavras-chave que indicam o vencedor real (aparece DEPOIS dessas palavras)
    winner_patterns = [
        r"['\"]([^'\"]+)['\"].*(?:ganha|vence|leva|conquista)",  # 'Nome' ganha/vence
        r"(?:ganha|vence|leva|conquista).*['\"]([^'\"]+)['\"]",  # ganha/vence... 'Nome'
        r"(?:desbanca.*e\s+vence|e\s+vence|e\s+ganha|e\s+leva)",  # X desbanca Y e vence
    ]

    # Se o título tem "desbanca", o vencedor é quem "vence/ganha", não quem foi desbancado
    if 'desbanca' in title_lower:
        # Padrão: "X desbanca Y e vence" -> X é o vencedor
        match = re.search(r"['\"]?([^'\"]+?)['\"]?\s+desbanca", title_lower)
        if match:
            desbancador = match.group(1).strip()
            for nome in PALPITES[category]:
                if nome.lower() in desbancador:
                    return nome

    # Busca padrão: primeiro nome mencionado junto com verbo de vitória
    # Priorizar nomes que aparecem perto de "ganha/vence/leva"
    for nome in PALPITES[category]:
        nome_lower = nome.lower()
        if nome_lower in title_lower:
            # Verificar se o nome aparece como vencedor (não como derrotado)
            # Se "desbanca" está no título e o nome aparece depois, ele foi derrotado
            if 'desbanca' in title_lower:
                pos_nome = title_lower.find(nome_lower)
                pos_desbanca = title_lower.find('desbanca')
                if pos_nome > pos_desbanca:
                    continue  # Este nome foi desbancado, pular
            return nome

    return None


def get_predictors(category, winner_name):
    """Retorna quem apostou no vencedor"""
    if category not in PALPITES or winner_name not in PALPITES[category]:
        return []
    return PALPITES[category][winner_name]


# ============================================================
# FORMATAÇÃO DE MENSAGEM
# ============================================================

def format_message(title, category, vencedor, acertaram, placar):
    """Formata a mensagem para o WhatsApp"""
    msg = f"🏆 *OSCAR 2026* 🏆\n\n"
    msg += f"📢 *{title}*\n\n"

    if category and vencedor:
        msg += f"🎬 *Categoria:* {category}\n"
        msg += f"🏅 *Vencedor(a):* {vencedor}\n\n"

        if acertaram:
            nomes = ', '.join(acertaram)
            msg += f"✅ *Acertou:* {nomes}\n"
            msg += f"👏 Parabéns!\n\n"
        else:
            msg += f"❌ *Ninguém acertou essa!*\n\n"

        msg += f"📊 *PLACAR ATUALIZADO:*\n"
        sorted_placar = sorted(placar.items(), key=lambda x: x[1], reverse=True)
        posicao = 1
        for i, (nome, pontos) in enumerate(sorted_placar):
            medal = ''
            if posicao == 1:
                medal = '🥇'
            elif posicao == 2:
                medal = '🥈'
            elif posicao == 3:
                medal = '🥉'
            else:
                medal = '  '

            pts_label = 'pt' if pontos == 1 else 'pts'
            msg += f"{medal} {nome}: {pontos} {pts_label}\n"

            # Verifica se o próximo tem pontuação diferente
            if i + 1 < len(sorted_placar) and sorted_placar[i + 1][1] < pontos:
                posicao = i + 2

    msg += f"\n🤖 _Oscar Tracker - Bolão Zacadentes_"
    return msg


# ============================================================
# WHATSAPP VIA SELENIUM
# ============================================================

_driver = None


def init_whatsapp():
    """Inicializa o Chrome com WhatsApp Web"""
    global _driver

    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    print("\n📱 Iniciando WhatsApp Web...")

    options = Options()
    options.add_argument(f'--user-data-dir={CHROME_PROFILE_DIR}')
    options.add_argument('--profile-directory=Default')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    # Manter aberto
    options.add_experimental_option('detach', True)

    service = Service(ChromeDriverManager().install())
    _driver = webdriver.Chrome(service=service, options=options)
    _driver.get('https://web.whatsapp.com/')

    print("=" * 50)
    print("📱 WhatsApp Web aberto!")
    print("👉 Se for a primeira vez, escaneie o QR Code")
    print("   com seu celular.")
    print("=" * 50)

    # Esperar o WhatsApp carregar (espera o painel lateral aparecer)
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By

    print("⏳ Aguardando login no WhatsApp...")
    try:
        WebDriverWait(_driver, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-tab="3"]'))
        )
        print("✅ WhatsApp conectado com sucesso!\n")
    except Exception:
        print("⚠️  Timeout esperando login. Tentando continuar mesmo assim...")

    # Navegar até o grupo
    navigate_to_group()


def navigate_to_group():
    """Navega até o grupo Zacadentes no WhatsApp"""
    global _driver

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print(f"🔍 Procurando grupo '{GRUPO_WHATSAPP}'...")

    try:
        time.sleep(2)

        # Clicar na barra de pesquisa
        search_box = WebDriverWait(_driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-tab="3"]'))
        )
        search_box.click()
        time.sleep(1)

        # Limpar e digitar o nome do grupo
        search_input = _driver.switch_to.active_element
        search_input.send_keys(Keys.CONTROL + 'a')
        search_input.send_keys(Keys.DELETE)
        time.sleep(0.5)
        search_input.send_keys(GRUPO_WHATSAPP)
        time.sleep(2)

        # Clicar no resultado (grupo)
        # Buscar por span que contenha o nome do grupo
        group_elem = WebDriverWait(_driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                f'//span[@title and contains(translate(@title, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{GRUPO_WHATSAPP.lower()}")]'
            ))
        )
        group_elem.click()
        time.sleep(2)

        # Limpar a pesquisa (apertar Escape)
        search_input = _driver.find_element(By.CSS_SELECTOR, 'div[data-tab="3"]')
        search_input.send_keys(Keys.ESCAPE)
        time.sleep(1)

        print(f"✅ Grupo '{GRUPO_WHATSAPP}' aberto!\n")
        return True

    except Exception as e:
        print(f"⚠️  Erro ao navegar para o grupo: {e}")
        print("   Tente abrir o grupo manualmente no WhatsApp Web.")
        return False


def send_whatsapp_message(message, _retry=False):
    """Envia uma mensagem no grupo aberto do WhatsApp usando clipboard (suporta emojis)"""
    global _driver

    if _driver is None:
        print("⚠️  WhatsApp não inicializado!")
        return False

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import subprocess

    try:
        # Encontrar o campo de mensagem via footer (mais confiável)
        footer = WebDriverWait(_driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, 'footer'))
        )
        msg_box = footer.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
        msg_box.click()
        time.sleep(1)

        # Copiar mensagem para o clipboard via PowerShell (suporta Unicode/emojis)
        # Escapar aspas simples para PowerShell
        escaped = message.replace("'", "''")
        powershell_cmd = f"Set-Clipboard -Value '{escaped}'"
        subprocess.run(
            ['powershell', '-Command', powershell_cmd],
            check=True, capture_output=True, timeout=5
        )
        time.sleep(0.3)

        # Colar com Ctrl+V (funciona com emojis!)
        msg_box.send_keys(Keys.CONTROL + 'v')
        time.sleep(1)

        # Enviar (Enter)
        msg_box.send_keys(Keys.ENTER)
        time.sleep(2)

        print("✅ Mensagem enviada no WhatsApp!")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        if not _retry:
            print("   Tentando reabrir o grupo...")
            try:
                navigate_to_group()
                return send_whatsapp_message(message, _retry=True)
            except Exception:
                pass
        return False


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def check_for_new_winners(state):
    """Verifica se há novos vencedores na BBC"""
    new_winners = []

    try:
        results = fetch_bbc_results()
    except Exception as e:
        print(f"  ⚠️  Erro ao buscar BBC: {e}")
        return new_winners

    for result in results:
        urn = get_urn(result)

        # Pular se já vimos esse post
        if urn in state['seen_urns']:
            continue

        title = get_header_text(result)
        timestamp = get_timestamp(result)

        # Verificar se é anúncio de vencedor
        if not is_winner_announcement(title):
            state['seen_urns'].append(urn)
            continue

        # Detectar categoria
        category = detect_category(title)
        if category is None:
            # Categoria não está no bolão, pular
            print(f"  ⏭️  Prêmio fora do bolão: {title[:80]}")
            state['seen_urns'].append(urn)
            continue

        # Verificar se já anunciamos essa categoria
        if category in state['categorias_anunciadas']:
            state['seen_urns'].append(urn)
            continue

        # Encontrar o vencedor
        winner = find_winner_name(category, title)
        if winner is None:
            # Vencedor não encontrado na lista - pode ser nome diferente
            print(f"  ⚠️  Vencedor não identificado na lista para '{category}': {title[:80]}")
            # Mesmo assim, marcar como visto mas NÃO marcar categoria como anunciada
            # para permitir pegar um post subsequente com mais detalhes
            state['seen_urns'].append(urn)
            continue

        # Encontrar quem acertou
        predictors = get_predictors(category, winner)

        # Atualizar placar
        for person in predictors:
            if person in state['placar']:
                state['placar'][person] += 1

        # Marcar categoria como anunciada
        state['categorias_anunciadas'].append(category)
        state['seen_urns'].append(urn)

        new_winners.append({
            'title': title,
            'category': category,
            'winner': winner,
            'predictors': predictors,
            'timestamp': timestamp,
        })

    return new_winners


def main():
    """Função principal"""
    print("=" * 55)
    print("  🏆  OSCAR TRACKER 2026 - BOLÃO ZACADENTES  🏆")
    print("=" * 55)
    print()

    # Carregar estado
    state = load_state()
    print(f"📊 Placar atual:")
    sorted_placar = sorted(state['placar'].items(), key=lambda x: x[1], reverse=True)
    for nome, pts in sorted_placar:
        print(f"   {nome}: {pts} pts")
    print(f"\n📋 Categorias já anunciadas: {len(state['categorias_anunciadas'])}")
    for cat in state['categorias_anunciadas']:
        print(f"   ✓ {cat}")
    print()

    # Modo teste?
    test_mode = '--test' in sys.argv
    no_whatsapp = '--no-whatsapp' in sys.argv

    if no_whatsapp:
        print("⚠️  Modo sem WhatsApp (apenas console)\n")
    elif not test_mode:
        # Inicializar WhatsApp
        init_whatsapp()

    if test_mode:
        # Enviar mensagem de teste
        print("🧪 Modo teste - enviando mensagem de teste...")
        init_whatsapp()
        test_msg = ("🏆 *OSCAR 2026* 🏆\n\n"
                    "🧪 *TESTE DO OSCAR TRACKER*\n\n"
                    "Se você está vendo essa mensagem, o bot está funcionando!\n\n"
                    "🤖 _Oscar Tracker - Bolão Zacadentes_")
        send_whatsapp_message(test_msg)
        print("\n✅ Teste concluído!")
        return

    # Loop de monitoramento
    print("🔄 Iniciando monitoramento da BBC...")
    print(f"   Verificando a cada {INTERVALO_CHECAGEM} segundos")
    print(f"   URL: {BBC_URL}")
    print(f"   Pressione Ctrl+C para parar\n")

    check_count = 0
    while True:
        try:
            check_count += 1
            now = datetime.now().strftime('%H:%M:%S')
            print(f"[{now}] Checagem #{check_count}...", end=' ')

            new_winners = check_for_new_winners(state)

            if new_winners:
                print(f"🎉 {len(new_winners)} novo(s) vencedor(es)!")
                for winner_info in new_winners:
                    print(f"\n  🏆 {winner_info['category']}: {winner_info['winner']}")

                    # Formatar mensagem
                    msg = format_message(
                        winner_info['title'],
                        winner_info['category'],
                        winner_info['winner'],
                        winner_info['predictors'],
                        state['placar']
                    )

                    # Mostrar no console
                    print("\n" + "-" * 40)
                    print(msg)
                    print("-" * 40)

                    # Enviar no WhatsApp
                    if not no_whatsapp:
                        print("\n  📤 Enviando no WhatsApp...")
                        send_whatsapp_message(msg)

                # Salvar estado atualizado
                save_state(state)
                print(f"\n  💾 Estado salvo.")
            else:
                print("Nenhum novo vencedor.")

            # Salvar URNs vistos mesmo sem novos vencedores
            save_state(state)

            # Aguardar
            time.sleep(INTERVALO_CHECAGEM)

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoramento encerrado pelo usuário.")
            save_state(state)
            print("💾 Estado salvo.")
            break
        except Exception as e:
            print(f"\n  ❌ Erro: {e}")
            print(f"  Tentando novamente em {INTERVALO_CHECAGEM}s...")
            time.sleep(INTERVALO_CHECAGEM)


if __name__ == '__main__':
    main()

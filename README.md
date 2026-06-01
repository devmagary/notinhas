# Sigeduc Auto 🤖🎓

Uma automação feita em Python para facilitar a vida dos professores da rede estadual da Bahia. O **Sigeduc Auto** preenche automaticamente as frequências (presenças e faltas) e lança as notas dos alunos no portal Sigeduc BA, lendo os dados diretamente de planilhas Excel (XLSX) ou arquivos de texto (CSV/TXT).

## ✨ Funcionalidades

- **Lançamento de Frequência em Massa:** Escolha múltiplas datas no calendário e o robô preenche as faltas e presenças para todos os alunos de uma vez.
- **Lançamento de Notas:** Lê as notas de um arquivo Excel (Simulado, Atividades, etc.) e digita nos campos corretos do portal.
- **Navegação Inteligente:** Sobrevive a quedas de conexão e recarregamentos da página, além de não precisar de scripts complexos instalados no navegador.
- **Sessão Salva:** Você só faz login uma vez! O robô guarda o perfil do seu navegador localmente, agilizando os próximos acessos.
- **Interface Gráfica Amigável:** Uma tela fácil de usar com barra de progresso, botão de cancelar (parada de emergência) e relatórios visuais.

## 🚀 Como Usar

### Pré-requisitos
Certifique-se de ter o [Python](https://www.python.org/downloads/) instalado na sua máquina (versão 3.8 ou superior).

### Instalação
O aplicativo instala as bibliotecas necessárias automaticamente no primeiro uso. Basta executar:

```bash
python sigeduc_gui.py
```
*(Ou dê um duplo clique no arquivo `sigeduc_gui.py` se o Windows estiver configurado para executar arquivos Python)*

### Passo a Passo

1. Abra o aplicativo.
2. Na aba **Operação**, escolha a tarefa: *Lançar Frequência* ou *Lançar Notas*.
3. Clique em **Procurar...** e selecione sua planilha Excel (`.xlsx`) ou lista de texto com os alunos.
4. (Para frequência) Clique em **Abrir Calendário** e adicione as datas que deseja lançar.
5. Selecione a senha (opcional, para gravação automática).
6. Clique em **▶ INICIAR AUTOMAÇÃO** e siga as instruções na tela. O navegador Chrome abrirá sozinho.

## 🛠️ Tecnologias Utilizadas

- **[Playwright](https://playwright.dev/python/)**: Para automação e controle do navegador Chrome sem a necessidade de drivers externos.
- **[CustomTkinter](https://customtkinter.tomschimansky.com/)**: Para a interface gráfica moderna com suporte a tema claro/escuro.
- **[OpenPyXL](https://openpyxl.readthedocs.io/)**: Para leitura e extração de dados de planilhas Excel.

## ⚠️ Avisos Importantes

- **Segurança:** Sua senha **não** é salva em nenhum arquivo. Ela é mantida apenas na memória durante a execução para que o robô possa clicar no botão "Gravar" por você.
- O projeto usa correspondência inteligente de nomes para evitar preencher a nota de "Maria" no campo de "Mariana".
- Se houver instabilidade no Sigeduc, a automação pausará e pedirá sua intervenção manual na interface para evitar a perda de dados.

## 📝 Licença
Este projeto é de uso livre. Desenvolvido para facilitar o fluxo de trabalho escolar.

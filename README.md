Descriere

Report Bot este un bot de Telegram care transforma fisierele Excel si CSV in rapoarte PDF profesionale, cu analiza detaliata generata de inteligenta artificiala. Botul detecteaza automat structura datelor, identifica domeniul (financiar, audit, HR, logistica etc.) si genereaza concluzii, tendinte si recomandari concrete.

## Incearca botul

[Deschide in Telegram](https://t.me/reportgeneratorgeneratorbot)

 Instalare locala

1. Cloneaza repository-ul
```bash
git clone https://github.com/crinises/telegram-report-bot.git
cd telegram-report-bot
```

2. Instaleaza dependentele
```bash
pip install -r requirements.txt
```

3. Creaza fisierul `.env`
```bash
TELEGRAM_TOKEN=tokenul_tau_telegram
GROQ_API_KEY=cheia_ta_groq
```

4. Porneste botul
```bash
python main.py
```

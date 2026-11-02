name: SBR Social Manager Auto

on:
  schedule:
    - cron: '30 8 * * 1,3,5,6'   # Lun, Mer, Ven, Sab genera la proposta
    - cron: '*/15 8-18 * * *'    # Controlla ogni 15 min se hai premuto "Approva" su Telegram
  workflow_dispatch:
    inputs:
      azione:
        description: 'Scegli cosa fare subito (genera / pubblica)'
        required: true
        default: 'genera'
        type: choice
        options:
          - genera
          - pubblica
      forza_formato:
        description: 'Formato post (solo se scegli genera)'
        required: false
        default: 'AUTO'
        type: choice
        options:
          - AUTO
          - PRE_MATCH
          - RISULTATI
          - OMEGA

permissions:
  contents: write

jobs:
  social_bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Installa dipendenze e browser grafico
        run: |
          pip install requests playwright tzdata
          playwright install chromium

      - name: Esegui generazione (Groq Free AI) o pubblicazione (Meta API)
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          ADMIN_CHAT_ID: ${{ secrets.ADMIN_CHAT_ID }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          GITHUB_RAW_BASE: https://raw.githubusercontent.com/${{ github.repository }}/main
        run: |
          if [ "${{ github.event.schedule }}" = "*/15 8-18 * * *" ] || [ "${{ github.event.inputs.azione }}" = "pubblica" ]; then
            python bot_social_manager.py pubblica
          else
            python bot_social_manager.py genera ${{ github.event.inputs.forza_formato }}
          fi

      - name: Salva immagine e stato nel repository
        run: |
          git config user.name "SBR Social Bot"
          git config user.email "bot@sbr.lab"
          git pull --rebase --autostash || true
          git add social_post_ready.png pending_social_post.json 2>/dev/null || true
          git diff --staged --quiet || git commit -m "Update bozza social SBR"
          git push

systemctl daemon-reload
systemctl restart mb_participants_bot
journalctl -u mb_participants_bot.service -f
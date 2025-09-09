#!/bin/bash
systemctl daemon-reload
systemctl restart cbc_crew_bot
journalctl -u cbc_crew_bot.service -f
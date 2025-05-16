#!/usr/bin/env bash
echo -n "show" | socat - UNIX-CONNECT:/tmp/clipboard_preview.sock

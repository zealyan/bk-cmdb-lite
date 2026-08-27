#!/bin/bash
set -x
cd /tmp/archive_download
rm -f archive.zip
URL='https://agent-sandbox-bj-d2-gw.trae.cn/explorer/6a582a0521600b51643655c8/archive.zip?authorization=Cloud-IDE-JWT+eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiMzY2OTQ4OTc4MTU4NzA4MCIsInNvdXJjZSI6InNlc3Npb24iLCJzb3VyY2VfaWQiOiJoYzBmUVIxTzlFUl9hUTZtaHk2RmlBN2JTaWktOWkwaU1WMXlqaWN6QXE0PS4xOGMwMzc3N2JkOTk5YWZhIiwidGVuYW50X2lkIjoiN28yZDg5NHA3ZHIwbzQiLCJ0eXBlIjoidXNlciJ9LCJleHAiOjE3ODQxOTA5NzgsImlhdCI6MTc4NDE2MjE3OH0.XaBbjdc_YzjnDb5JA8H7jVpkvDfX1F5VrGz1_f6Mf3yFqatDowl-BRoPzuKBLnqy0NqPMl-wHaflgoDJhraKcVJUjFoIA4BAtakieqPCNjp1eybGhphRuKuuOz2RYsU2IFWUIpVsYhF09tSe1HZ2VWMTuleKaWn7Huz6MfXyfHZSAzIuHwSbt9yrfXHJzA1Y1EEfiJwN1dmwyAil-IyBSPkAfrzOvElzkz_eF8bSwQmF1Rob_EOBWNMteZx23EgjJkTLGn2umZf71XXYxAPtg2h0tcBFzjHy1zz2rpyC8aaaGgZ7ZfTlwD10qRI6qeM-3NmqP4jFhBYNAJ6m1EBQqYOVmtyzMtZ2M5GfwHGXgwp1YQQJ_4FuL6K4BcDoEgkDH-vTgyVFFXbvbgGh-MMghoJsfK3byTe0XI-_Nq6g15GQnBk3kRn5Vd-dxvkqDs8Orwx0lxUx3TnZb8vfJqcC1OjeWHcelImQXXNaHFZ-QsXYZVDlnoR0xcZcy7CQtOe8nh3GyezuW_beOPZzUN8W8mV81J-Ho1OoUiii_GjtPpYhfHXhW9kR-nVNb1-c9vhXdZABkLqa4Y9PsWBm0Yzy1PFVfEffJNF4I9G6WIv5XEQkxCpJj05SIYjrx-E32Nl7VcO7gobXUWKNTOL5WGcYu79DhBjbQKJPgD8S2M_8q0w&filename=%E6%8B%89%E5%8F%96%E5%BC%80%E5%8F%91%E5%88%86%E6%94%AF.zip'
echo "URL length: ${#URL}"
curl -v --noproxy "*" --connect-timeout 30 --max-time 600 -o archive.zip "$URL" 2>&1 | tail -25
echo "exit=$?"
ls -la archive.zip 2>/dev/null
file archive.zip 2>/dev/null

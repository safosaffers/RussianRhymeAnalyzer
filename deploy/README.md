# Деплой лендинга Rhymer на VPS

Чистая статика (HTML+CSS+немного JS), без build-шага. Раздаётся nginx.

## 1. Загрузить сайт на сервер

```bash
# из корня проекта
scp -r site user@vps:/tmp/rhymer-site
ssh user@vps 'sudo rm -rf /var/www/rhymer && sudo mv /tmp/rhymer-site /var/www/rhymer'
```

Архивы сборок в git не хранятся - заливаем отдельно в `downloads/`:

```bash
scp dist/Rhymer-linux-x86_64.zip user@vps:/var/www/rhymer/downloads/
# позже: scp Rhymer-windows-x86_64.zip user@vps:/var/www/rhymer/downloads/
```

## 2. Подключить конфиг nginx

```bash
scp deploy/nginx-rhymer.conf user@vps:/tmp/
ssh user@vps
sudo mv /tmp/nginx-rhymer.conf /etc/nginx/sites-available/rhymer
# заменить server_name на свой домен
sudo ln -sf /etc/nginx/sites-available/rhymer /etc/nginx/sites-enabled/rhymer
sudo nginx -t && sudo systemctl reload nginx
```

Проверка: открыть `http://<домен-или-IP>/` - должен открыться лендинг.

## 3. HTTPS (необязательно)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d rhymer.example.com
```

Certbot сам допишет server-блок на 443 и настроит редирект с 80.

## Обновление сайта

```bash
scp -r site/* user@vps:/var/www/rhymer/    # ассеты/HTML
# downloads/ и nginx-конфиг обычно менять не нужно
```

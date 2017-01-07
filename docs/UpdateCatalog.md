# Manually updating the Catalog

Most of the scripts automatically update the catalog by calling `update_catalog()`. If you need to update the catalog without running a publishing script, follow these steps:

1. Log in to us.door43.org.
```bash
ssh username@us.door43.org -A
```
2. Get superuser access and start python.
```bash
sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash
python
```
3. Run these python commands in the terminal window.
```python
from uw import update_catalog
update_catalog.update_catalog()
exit()
```
4. Finally, set the permissions on the files.
```bash
chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/
```

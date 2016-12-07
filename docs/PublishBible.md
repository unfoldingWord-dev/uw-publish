# Steps for Publishing Bibles

**Don't forget to notify interested parties when finished, including publishing@unfoldingword.org.**

    python execute.py import_bible \
    --gitrepo https://git.door43.org/phillip-hopper/bible_sr-Latn \
    --domain pdb
    
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/

On pki.unfoldingword.org run

    sudo /root/tools/uw/sign.py

### Regenerate bible.unfoldingword.org

* Run these commands on the us.door43.org server:
    ```
    su unfoldingword
    cd /var/www/vhosts/bible.unfoldingword.org
    make build
    ```

* Run these commands locally:
    ```
    cd ~/Projects/uw-web && git pull && make publish
    ```

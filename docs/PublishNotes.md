# Steps for Publishing tN, tW and tQ

### Steps for Publishing tN

    cd uw-publish
    python execute.py publish_tn --version 6
    
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/
    
On pki.unfoldingword.org run

    sudo /root/tools/uw/sign.py

### Steps for Publishing tW

    cd uw-publish
    python execute.py publish_tw --version 6 --tag v6
    
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/
    
On pki.unfoldingword.org run

    sudo /root/tools/uw/sign.py

### Steps for Publishing tQ

    cd uw-publish
    python execute.py publish_tq --version 6 --tag v6
    
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/
    
On pki.unfoldingword.org run

    sudo /root/tools/uw/sign.py

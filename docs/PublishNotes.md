# Steps for Publishing tN, tW and tQ

    cd uw-publish
    python execute.py export_tn_tw_tq
    
    python /var/www/vhosts/door43.org/tools/uw/update_catalog.py
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/
    
On pki.unfoldingword.org run

    sudo /root/tools/uw/sign.py

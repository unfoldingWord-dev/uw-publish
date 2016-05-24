# Steps for Publishing ULB

__Don't forget to notify interested parties when finished, including publishing@unfoldingword.org.__

    python execute.py import_bible \
    --resource https://github.com/spthmpsn/Hu1Bible/archive/master.zip \
    --lang [LANGCODE] \
    --slug ulb \
    --version '3.1' \
    --source en \
    --check_level 1 \
    --checking 'Translation Team' \
    --name 'Unlocked Literal Bible - [LANG NAME (ex. Hungarian Karoli)]' \
    --translators 'www.unboundbible.org'

    python /var/www/vhosts/door43.org/tools/uwb/api_publish.py \
    --sourceDir /var/www/vhosts/api.unfoldingword.org/httpdocs/ulb/txt/1/ulb-[LANGCODE]

    python execute.py update_catalog
    
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/

On pki.unfoldingword.org run

    sudo /root/tools/uw/sign.py

### Regenerate bible.unfoldingword.org

* Run these commands on the us.door43.org server:


    su unfoldingword
    cd /var/www/vhosts/bible.unfoldingword.org
    make build

* Run these commands locally:


    cd ~/Projects/uw-web && make publish
    

### Removing a Bible from bible.unfoldingword.org

* Run these commands on the us.door43.org server:


    cd /var/www/vhosts/bible.unfoldingword.org/app/content/texts
    rm -rf uw_lang_ulb (or uw_* to remove and regenerate all)
    
* Regenerate using the steps above for __Regenerate bible.unfoldingword.org__


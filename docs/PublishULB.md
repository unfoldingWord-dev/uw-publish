# Steps for Publishing ULB

    python /var/www/vhosts/door43.org/tools/uwb/usfm_tS_import.py \
    --resource https://github.com/spthmpsn/Hu1Bible/archive/master.zip \
    --lang [LANGCODE] \
    --slug ulb \
    --version '3.1' \
    --source en \
    --check_level 1 \
    --checking 'Translation Team' \
    --name 'Unlocked Literal Bible - Hungarian Karoli' \
    --translators 'www.unboundbible.org'

    python /var/www/vhosts/door43.org/tools/uwb/api_publish.py \
    --sourceDir /var/www/vhosts/api.unfoldingword.org/httpdocs/ulb/txt/1/ulb-[LANGCODE]

    python /var/www/vhosts/door43.org/tools/uw/update_catalog.py
    
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/

On pki.unfoldingword.org run `sudo /root/tools/uw/sign.py`

### Regenerate bible.unfoldingword.org
    npm cache clean
    su unfoldingword
    cd /var/www/vhosts/bible.unfoldingword.org/tools/textgenerator
    /usr/bin/node uw-grab-bibles.js
    /usr/bin/node generate.js -u
    /usr/bin/node create_texts_index.js

Locally: `cd ~/Projects/uw-web && make publish`


https://github.com/spthmpsn/Rs1Bible/archive/master.zip
https://github.com/spthmpsn/Hu1Bible/archive/master.zip 
https://git.door43.org/80000BC16826/uw-luk-lpx/archive/master.zip
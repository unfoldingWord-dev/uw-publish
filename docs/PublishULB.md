# Steps for Publishing ULB from chunked source files

**Don't forget to notify interested parties when finished, including publishing@unfoldingword.org.**

    python execute.py import_bible_source \
    --resource https://github.com/Door43/ulb-[LANGCODE]/archive/master.zip \
    --lang [LANGCODE] \
    --slug ulb \
    --version '3.1' \
    --source en \
    --check_level 1 \
    --checking 'Translation Team' \
    --name 'Unlocked Literal Bible' \
    --translators 'www.unboundbible.org'
    
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/

On pki.unfoldingword.org run

    sudo /root/tools/uw/sign.py

### Regenerate bible.unfoldingword.org

* Run these commands on the us.door43.org server:


    su unfoldingword
    cd /var/www/vhosts/bible.unfoldingword.org
    make build

* Run these commands locally:


    cd ~/Projects/uw-web && git pull && make publish
    
### Create a new git release. 

For an example see https://github.com/unfoldingWord-dev/door43.org/wiki/Content-Release-Structure

### Removing a Bible from bible.unfoldingword.org

* Run these commands on the us.door43.org server:


    cd /var/www/vhosts/bible.unfoldingword.org/app/content/texts
    rm -rf uw_lang_ulb (or uw_* to remove and regenerate all)
    
* Regenerate using the steps above for __Regenerate bible.unfoldingword.org__


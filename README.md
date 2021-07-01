# comdirect financial report
this script generates an overview diagramm of your last 5 month income/expenses with the help of comdirect-rest api. you will be notified via telegram. very handy is a ssh shortcut on your phone in order to trigger the script on the fly. right now only pushtan is implemented. feel free to adapt the script to your needs.

![comdirect financial report](https://github.com/phpanhey/comdirect_financialreport/blob/master/example_chart.jpg?raw=true)

# usage 
```shell
python3 comdirect_financialreport.py 
```
## config
as a default the script depends on a `config.json` on its root directory in order to work properly. additionally a custom config can be specified as a param like so: `python3 comdirect_financialreport.py custom_config.json`. in order to use the comdirect api you need to register [here](https://www.comdirect.de/cms/kontakt-zugaenge-api.html).

here's an example of the config.
```json
{
    "username": "comdirect_user_name",
    "password": "comdirect_user_pin",
    "client_id": "user_xxxxxxxxxxxxxxxxxxx",
    "client_secret": "comidrect_client_secret",
    "telegram": {
        "bot_token": "telegram_bot_token",
        "bot_chat_id": "telegram_chat_id"
    }
}
```

## dependencies
```sh
pip3 install python-dateutil
pip3 install matplotlib
```
furthermore ``curl`` is required on command line.

## thanks
thanks [keisentraut](https://github.com/keisentraut/python-comdirect-api) for oauth implementation.



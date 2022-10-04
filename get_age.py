import requests
import re
from datetime import datetime

sFTTag_url = "https://login.live.com/oauth20_authorize.srf?client_id=000000004C12AE6F" \
             "&redirect_uri=https://login.live.com/oauth20_desktop.srf" \
             "&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"


def get_urlPost_sFTTag(session):
    r = session.get(sFTTag_url)
    text = r.text
    match = re.match(r'.*value="(.+?)".*', text, re.S)
    if match is not None:
        sFTTag = match.group(1)
        match = re.match(r".*urlPost:'(.+?)'.*", text, re.S)
        if match is not None:
            return match.group(1), sFTTag


def get_xbox_rps(session, email, password, urlPost, sFTTag):
    login_request = session.post(urlPost, data={
        'login': email,
        'loginfmt': email,
        'passwd': password,
        'PPFT': sFTTag
    }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True)
    if '#' in login_request.url and login_request.url != sFTTag_url:
        token = None
        for item in login_request.url.split("#")[1].split("&"):
            key, value = item.split("=")
            if key == 'access_token':
                token = requests.utils.unquote(value)
                break
        return token
    else:
        raise ValueError('Your credentials are incorrect')


def authenticate(email, password):
    session = requests.Session()

    token = get_xbox_rps(session, email, password, *get_urlPost_sFTTag(session))
    if token is not None:
        xbox_login = session.post('https://user.auth.xboxlive.com/user/authenticate', json={
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": token
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }, headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
        js = xbox_login.json()
        xbox_token = js.get('Token')
        if xbox_token is not None:
            uhs = js['DisplayClaims']['xui'][0]['uhs']
            xsts = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json={
                "Properties": {
                    "SandboxId": "RETAIL",
                    "UserTokens": [xbox_token]
                },
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT"
            }, headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
            js = xsts.json()
            xsts_token = js.get('Token')
            if xsts_token is not None:
                mc_login = session.post('https://api.minecraftservices.com/authentication/login_with_xbox',
                                        json={'identityToken': f"XBL3.0 x={uhs};{xsts_token}"},
                                        headers={'Content-Type': 'application/json'})
                access_token = mc_login.json().get('access_token')
                if access_token is not None:
                    return access_token


def get_account_age(access_token):
    r = requests.get('https://api.minecraftservices.com/minecraft/profile/namechange',
                     headers={'Authorization': f'Bearer {access_token}'})
    if r.status_code == 200:
        return datetime.fromisoformat(r.json()['createdAt'][:-1])


if __name__ == '__main__':
    access_token = authenticate('<email>', '<password>')
    create_date = get_account_age(access_token)
    print(f'Account created: {create_date}')

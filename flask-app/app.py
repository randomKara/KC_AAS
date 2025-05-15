from flask import Flask, session, redirect, request, url_for, jsonify
import os
from functools import wraps
import requests
import time
import json
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# OIDC Configuration using Dex as the broker
OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL", "http://localhost:5556/dex/.well-known/openid-configuration")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "flask-app")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "flask-app-secret")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:5000/callback")

# Setup OAuth
oauth = OAuth(app)

# Register Dex as an OAuth provider
dex = oauth.register(
    name='dex',
    server_metadata_url=OIDC_DISCOVERY_URL,
    client_id=OIDC_CLIENT_ID,
    client_secret=OIDC_CLIENT_SECRET,
    client_kwargs={
        'scope': 'openid email profile',
        'token_endpoint_auth_method': 'client_secret_basic'
    }
)

# La fonctionnalité de décorateur pour sécuriser les routes
def login_required(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if session.get('user'):
            return fn(*args, **kwargs)
        return redirect('/login')
    return decorated_view

@app.route('/')
@login_required
def home():
    return f'Bonjour {session["user"]["name"]} ! Vous êtes connecté à l\'application via Keycloak et Dex.'

@app.route('/profile')
@login_required
def profile():
    return jsonify(session.get('user'))

@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return dex.authorize_redirect(redirect_uri)

@app.route('/callback')
def callback():
    try:
        # Get the token from Dex
        token = dex.authorize_access_token()
        
        # Get user info from userinfo endpoint
        user_info = dex.parse_id_token(token, nonce=session.get('nonce'))
        
        # Add access token to user info
        user_info['access_token'] = token.get('access_token')
        
        # Store user info in session
        session['user'] = {
            'name': user_info.get('name', 'Utilisateur'),
            'email': user_info.get('email', ''),
            'username': user_info.get('preferred_username', user_info.get('sub', '')),
            'sub': user_info.get('sub'),
            'token': token
        }
        return redirect('/')
    except Exception as e:
        return f"Erreur lors de l'authentification: {str(e)}", 500

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/health')
def health():
    # Vérifier les configurations et connexions
    health_info = {
        "status": "ok",
        "oidc_discovery_url": OIDC_DISCOVERY_URL,
        "client_id": OIDC_CLIENT_ID,
        "redirect_uri": OIDC_REDIRECT_URI
    }
    
    # Vérifier si le discovery endpoint est accessible
    try:
        discovery_response = requests.get(OIDC_DISCOVERY_URL, timeout=5)
        health_info["discovery_status"] = discovery_response.status_code
        health_info["discovery_accessible"] = True
        
        if discovery_response.status_code == 200:
            oidc_config = discovery_response.json()
            health_info["discovery_endpoints"] = {
                "authorization_endpoint": oidc_config.get("authorization_endpoint"),
                "token_endpoint": oidc_config.get("token_endpoint"),
                "userinfo_endpoint": oidc_config.get("userinfo_endpoint"),
                "jwks_uri": oidc_config.get("jwks_uri")
            }
    except Exception as e:
        health_info["discovery_status"] = "error"
        health_info["discovery_error"] = str(e)
        health_info["discovery_accessible"] = False
    
    return jsonify(health_info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 
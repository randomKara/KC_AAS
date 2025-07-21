# KC_AAS: Centralized Authentication with Keycloak and Dex

This project implements a centralized authentication solution using Keycloak as the identity provider and Dex as an OIDC gateway. A Flask application is used to demonstrate the integration.

## Architecture

- **Keycloak**: Identity provider that manages users, roles, and permissions
- **Dex**: OIDC server that federates Keycloak and client applications
- **Flask App**: Sample application demonstrating authentication integration

## Prerequisites

- Docker
- Docker Compose
- Python 3.x

## Installation and Setup

### 1. Preparation

1. Clone the repository
2. Add the following lines to your `/etc/hosts` file:

```
127.0.0.1 keycloak
127.0.0.1 dex
```

### 2. Start Keycloak & Flask Application

Start Keycloak (the main identity provider) first:

```bash
docker compose up -d
```

Wait for Keycloak to be fully started (approximately 1-2 minutes).

### 3. Configure and Launch Dex

#### Generate Dex Configuration

Use the `create_dex_config.py` script to generate the Dex configuration and register the client in Keycloak:

```bash
python3 scripts/create_dex_config.py \
  --dex-name dex \
  --dex-issuer-url http://dex:5556 \
  --keycloak-url http://keycloak:8080 \
  --static-client-id flask-app \
  --static-client-name "Flask App" \
  --static-client-secret flask-app-secret \
  --static-client-redirect-uris http://localhost:5000/callback \
  --oauth-skip-approval-screen \
  --file dex/config.yaml
```

#### create_dex_config.py - Complete Arguments Reference

The `create_dex_config.py` script supports extensive configuration options:

##### Required Arguments

- `--dex-name`: Name of the DEX broker (used for identifiers) - **Required**

##### DEX Configuration Arguments

- `--dex-port`: DEX listening port (default: 5556)
- `--dex-host`: DEX listening host (default: 0.0.0.0)
- `--dex-issuer-url`: Public DEX URL (default: http://HOSTNAME:PORT)
- `--dex-tls-cert`: Path to TLS certificate (optional)
- `--dex-tls-key`: Path to TLS key (optional)

##### Keycloak (IdP) Arguments

- `--keycloak-url`: Keycloak URL (default: http://localhost:8080)
- `--keycloak-realm`: Keycloak realm (default: KC_AAS)
- `--keycloak-admin-user`: Keycloak admin username (default: admin)
- `--keycloak-admin-password`: Keycloak admin password (default: admin)

##### Client Configuration Arguments

- `--client-id`: Client ID for Keycloak registration (default: uses dex-name)
- `--client-secret`: Client secret (randomly generated if not provided)

##### Static Client Arguments

- `--static-client-id`: Static client ID (e.g., flask-app)
- `--static-client-name`: Static client display name (e.g., "Flask App")
- `--static-client-secret`: Static client secret
- `--static-client-redirect-uris`: Redirect URIs for the static client (can specify multiple)

##### Security and OAuth2 Arguments

- `--oauth-skip-approval-screen`: Skip OAuth approval screen (flag)
- `--session-expiry`: Session expiration duration (default: 24h, e.g., 30m, 2h)
- `--oauth-response-types`: OAuth2 response types (default: code, token, id_token)
- `--enable-password-db`: Enable local password database (flag)

##### Storage Configuration Arguments

- `--storage-type`: Storage type (choices: memory, sqlite3, postgres, mysql, default: memory)
- `--storage-config`: JSON configuration for storage (depends on type)

##### Logging Arguments

- `--log-level`: Log level (choices: debug, info, warn, error, default: debug)
- `--log-format`: Log format (choices: text, json, default: text)

##### Claims Mapping Arguments

- `--claim-groups`: Claim name for groups (default: groups)
- `--claim-username`: Claim name for username (default: preferred_username)
- `--claim-email`: Claim name for email (default: email)
- `--claim-name`: Claim name for full name (default: name)

##### Docker and Output Arguments

- `--docker-network`: Docker network name (default: auth-network)
- `--file`: Output file for saving YAML configuration (e.g., dex/config.yaml)

#### Example Usage Scenarios

##### Basic Configuration
```bash
python3 scripts/create_dex_config.py --dex-name my-dex
```

##### Production Configuration with TLS
```bash
python3 scripts/create_dex_config.py \
  --dex-name production-dex \
  --dex-port 443 \
  --dex-issuer-url https://dex.mydomain.com \
  --dex-tls-cert /path/to/cert.pem \
  --dex-tls-key /path/to/key.pem \
  --keycloak-url https://keycloak.mydomain.com \
  --storage-type sqlite3 \
  --log-level info \
  --file dex/config.yaml
```

##### Configuration with Custom Storage
```bash
python3 scripts/create_dex_config.py \
  --dex-name postgres-dex \
  --storage-type postgres \
  --storage-config '{"host":"postgres","port":5432,"user":"dex","password":"secret","database":"dex","ssl":"require"}' \
  --file dex/config.yaml
```

#### Register Client in Keycloak

After running the script, execute the displayed Keycloak registration command to register the client:

```bash
# The script will output a command similar to:
python3 scripts/create_client_in_kc_aas.py \
    --client-id dex \
    --client-name "DEX Broker dex" \
    --redirect-uris "http://dex:5556/callback" "http://dex:5556/login/callback" \
    --root-url "http://dex:5556" \
    --base-url "http://dex:5556" \
    --keycloak-url "http://keycloak:8080" \
    --admin-user "admin" \
    --admin-password "admin" \
    --realm "KC_AAS" \
    --quiet
    --cliient-secret "the secret given in dex config"
```

#### Launch Dex Container

After configuration, launch Dex using the provided Docker command:

```bash
docker run -d \
  --name dex \
  --network auth-network \
  -p 5556:5556 \
  -v $(pwd)/dex/config.yaml:/etc/dex/config.yaml \
  ghcr.io/dexidp/dex:v2.37.0 \
  dex serve /etc/dex/config.yaml
```

For TLS configurations, add the certificate volumes:

```bash
docker run -d \
  --name dex \
  --network auth-network \
  -p 443:443 \
  -v $(pwd)/dex/config.yaml:/etc/dex/config.yaml \
  -v /path/to/cert:/etc/dex/tls.crt \
  -v /path/to/key:/etc/dex/tls.key \
  ghcr.io/dexidp/dex:v2.37.0 \
  dex serve /etc/dex/config.yaml
```

## Usage

### Access the Applications

1. **Flask App**: http://localhost:5000
2. **Keycloak Admin**: http://localhost:8080/admin (admin/admin)
3. **Dex**: http://localhost:5556/.well-known/openid_configuration

### Authentication Flow

1. Navigate to the Flask application
2. Click "Login" to initiate authentication
3. You'll be redirected to Dex, then to Keycloak
4. Enter your Keycloak credentials
5. After successful authentication, you'll be redirected back to the Flask app

### Default Credentials

- **Keycloak Admin**: admin/admin
- **Test User**: user/password (created during realm import)

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure all containers are running and accessible
2. **Certificate Errors**: Check TLS configuration and certificate paths
3. **Authentication Failures**: Verify client registration and secrets match
4. **Port Conflicts**: Ensure ports 5000, 5556, and 8080 are available

### Checking Container Status

```bash
# Check all containers
docker ps

# Check Keycloak logs
docker logs keycloak

# Check Dex logs
docker logs dex

# Check Flask app logs
docker logs flask-app
```

## Security Considerations

- Change default passwords in production
- Use proper TLS certificates
- Configure proper network security
- Review and adjust token expiration times
- Enable appropriate logging for audit trails

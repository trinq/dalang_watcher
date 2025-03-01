# Deploying Dalang Watcher to a VPS

This guide explains how to deploy the Dalang Watcher application to a Virtual Private Server (VPS) with a public IP address.

## Prerequisites

- A VPS with Docker and Docker Compose installed
- Git installed on the VPS
- A domain name (optional but recommended)

## Deployment Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/dalang_watcher.git
cd dalang_watcher
```

### 2. Configure Environment Variables

Create a production environment file:

```bash
cp env.production.example .env
```

Edit the `.env` file and set secure values:

```bash
# Use a strong password
nano .env
```

Make sure to:
- Change the database password
- Set an API key
- Configure any other environment-specific settings

### 3. Configure Docker Compose

The docker-compose.yml file is already configured for production use, but you may want to review it:

```bash
nano docker-compose.yml
```

Key security settings:
- Database port is only exposed to localhost (`127.0.0.1:5432:5432`)
- Restart policies are set to `always`

### 4. Deploy with Docker Compose

```bash
docker-compose up -d
```

This will:
- Build the API container
- Start the TimescaleDB container
- Link them together on a Docker network

### 5. Set Up a Reverse Proxy (Recommended)

For production deployments, it's recommended to use a reverse proxy like Nginx:

```bash
apt update
apt install -y nginx certbot python3-certbot-nginx
```

Create an Nginx configuration:

```bash
nano /etc/nginx/sites-available/dalang-watcher
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and get SSL certificate:

```bash
ln -s /etc/nginx/sites-available/dalang-watcher /etc/nginx/sites-enabled/
certbot --nginx -d your-domain.com
nginx -t
systemctl reload nginx
```

### 6. Test the Deployment

Test the API using curl:

```bash
# Health check (no authentication required)
curl http://localhost:5000/api/health

# Authenticated request (replace YOUR_API_KEY with your actual API key)
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:5000/api/scans
```

### 7. Using the Python Client

To use the Python client with your production deployment:

```bash
# Set environment variables
export API_URL="https://your-domain.com"
export API_KEY="your-api-key"

# Run commands
./docs/examples/api_client.py scan-ports 192.168.1.1 --ports 80,443
```

## Monitoring and Maintenance

### Viewing Logs

```bash
# View API logs
docker logs asm_api

# View database logs
docker logs timescaledb
```

### Updating the Application

```bash
git pull
docker-compose down
docker-compose up -d --build
```

### Backup and Restore

Backup the database:

```bash
docker exec timescaledb pg_dump -U postgres dalang_watcher > backup.sql
```

Restore from backup:

```bash
cat backup.sql | docker exec -i timescaledb psql -U postgres dalang_watcher
```

## Security Considerations

1. **API Key**: Always use the API key authentication in production
2. **Database Password**: Use a strong password for the database
3. **Firewall**: Configure a firewall to restrict access to your server
4. **Regular Updates**: Keep your system and Docker images updated

## Integrating with n8n and Other Automation Tools

Dalang Watcher can be integrated with n8n and other automation tools to create powerful security monitoring workflows.

### Setting Up n8n for Port Change Detection

The example workflow in `docs/examples/n8n_example.json` demonstrates how to set up a comprehensive port monitoring system that:

1. Reads a list of target IPs from a CSV file
2. Scans each IP for open ports
3. Compares current scan results with previous scan results
4. Detects new open ports and previously open ports that are now closed
5. Sends consolidated alerts when changes are detected

#### Prerequisites

1. n8n installed and running (see [n8n documentation](https://docs.n8n.io/getting-started/installation/))
2. Dalang Watcher API running with `AUTOMATION_FRIENDLY=true` in your environment settings
3. A CSV file with target IPs in the format:
   ```
   ip
   192.168.1.1
   192.168.1.2
   ```

#### Importing the Workflow

1. In n8n, go to "Workflows" and click "Import from File"
2. Select the `docs/examples/n8n_example.json` file
3. Update the following:
   - Set the `DALANG_API_URL` and `DALANG_API_KEY` credentials in n8n
   - Update the Slack webhook URL or replace with your preferred notification method
   - Adjust the file path for the target IPs CSV file

#### Customizing the Workflow

The workflow is designed to be modular and can be customized:

- Change the scan frequency in the "Schedule Trigger" node
- Modify the port list in the "Scan Ports" node
- Adjust the alert format in the "Format Alert" node
- Add additional notification channels or integrations

### API Endpoints for Automation

The following endpoints are useful for automation:

- `POST /api/scan/ports` - Start a new port scan
- `GET /api/results?scan_id={scan_id}` - Get results for a specific scan
- `GET /api/scans?target={ip}` - Get scan history for a target IP

### Authentication with Automation Tools

When configuring authentication in your automation tool:

1. **Header Authentication**: Use the `X-API-Key` header with your API key
2. **Custom Authentication**: Some tools may require custom auth configuration
   - For n8n: Use the "Header Auth" authentication type
   - For Zapier: Use "API Key" authentication in the "Headers" section

#### Obtaining Your API Key

The API key is defined in your Dalang Watcher environment variables:

1. When you first deploy Dalang Watcher, you set the API key in your `.env` file:
   ```
   API_KEY=your_strong_api_key_here
   ```

2. If you haven't set an API key yet:
   - Edit your `.env` file on the server
   - Uncomment and set the `API_KEY` variable with a strong, random string
   - Restart the Dalang Watcher container to apply the changes:
     ```bash
     docker-compose restart api
     ```

3. To view your current API key (if you've forgotten it):
   ```bash
   docker-compose exec api sh -c 'echo $API_KEY'
   ```

4. When configuring n8n:
   - Create a new credential in n8n for "Header Auth"
   - Set the name to "X-API-Key" and the value to your API key
   - Reference this credential in your HTTP Request nodes

### Example: Detecting New Open Ports

The delta detection logic implemented in the n8n workflow follows this process:

1. Run a new scan for each target IP
2. Retrieve the most recent previous scan for comparison
3. Extract open ports from both scans
4. Compare to identify:
   - New open ports (in current scan but not in previous scan)
   - Closed ports (in previous scan but not in current scan)
5. Aggregate changes across all monitored IPs
6. Send a consolidated alert with detailed information

This approach allows for efficient monitoring of large IP ranges while only alerting when actual changes occur.

## Troubleshooting

### Database Connection Issues

If the API cannot connect to the database:

1. Check if the database container is running:
   ```bash
   docker ps | grep timescaledb
   ```

2. Verify database logs:
   ```bash
   docker logs timescaledb
   ```

3. Check the database connection parameters in the `.env` file

### Network Scanning Issues

If stealth scans are not working:

1. Verify that the container has the necessary capabilities:
   ```bash
   docker inspect asm_api | grep -A 10 CapAdd
   ```

2. Try using "connect" scan type instead of "stealth" for troubleshooting

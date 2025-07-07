# waterbot

Water level control device, weighs the bottle.

ToDo: add schematic and more details.

## Installation

1. Clone this repo
2. ``cd waterbot``
3. Init venv
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install uv if not installed: https://docs.astral.sh/uv/getting-started/installation/
5. Install requirements
   ```
   uv pip install .
   ``` 


## Testing

Send water level data to the backend with command:
`curl -X POST -d '{"water_level":12}' http://your-domain.com:9421/sensor`
Make sure to replace `your-domain.com` with the actual domain or IP address of your backend server.
Don't forget to open the port 9421 in your firewall.
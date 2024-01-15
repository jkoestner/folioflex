Plaid was set up from the pattern guide shown below.

https://github.com/plaid/pattern

There are 3 docker files in the folder that are used

- client
- server
- database

If wanting to run the integration in development npm needs to be installed.

If running on windows the package.json needs to be update to be compatiable with windows.

```json
"start": "set PORT=3001 && react-scripts start",
"proxy": "http://<ip server>:5001"
```

Then from the root directory run

```bash
npm start
```
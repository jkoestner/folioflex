Plaid was set up from the pattern guide shown below.

https://github.com/plaid/pattern

There are 3 docker files in the folder that are used

- client
- server
- database

# RUN LOCALLY

If wanting to run the integration in development npm needs to be installed.

Then from the root directory run

```bash
npm start
```

If looking to update packages, the following command reviews outdated packages

```bash
npm outdated
```

to install the latest package

```bash
npm install [package]@latest
```

## CLIENT
If running on windows the `package.json` needs to be update to be compatiable with windows.

```json
"start": "set PORT=3001 && react-scripts start",
"proxy": "http://<ip server>:5001"
```

## SERVER
If running on window the `index.js` should be updated to run locally

from
```
const { PORT } = process.env;
```

to
```
const { PORT } = 5001;
```
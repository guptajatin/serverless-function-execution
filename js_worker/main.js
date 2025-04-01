const express = require('express');
const bodyParser = require('body-parser');
const { VM } = require('vm2');
const app = express();
app.use(bodyParser.json());

app.post('/execute', (req, res) => {
    const { code, input } = req.body;
    const vm = new VM();
    try {
        const result = vm.run(`const main = ${code}; main(${JSON.stringify(input)});`);
        res.json({ result });
    } catch (err) {
        res.json({ error: err.message });
    }
});

app.listen(8000, () => console.log("JS worker listening on port 8000"));
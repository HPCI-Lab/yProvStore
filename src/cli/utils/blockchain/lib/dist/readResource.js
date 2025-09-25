"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.readResource = void 0;
// readResource.ts
const gatewayHelper_1 = require("./gatewayHelper");
const util_1 = require("util");
const utf8Decoder = new util_1.TextDecoder();
async function readResource(params) {
    const { pid } = params;
    if (!pid) {
        throw new Error('Missing PID parameter');
    }
    const { contract, gateway, client } = await (0, gatewayHelper_1.getContract)();
    try {
        const result = await contract.submitAsync('ReadResource', { arguments: [pid] });
        const status = await result.getStatus();
        if (!status.successful) {
            throw new Error(`Transaction ${status.transactionId} failed with status code ${status.code}`);
        }
        const resource = utf8Decoder.decode(result.getResult());
        return JSON.parse(resource);
    }
    finally {
        gateway.close();
        client.close();
    }
}
exports.readResource = readResource;
// Only run main() when file is executed directly (not imported)
if (require.main === module) {
    async function main() {
        const pid = process.argv[2];
        if (!pid) {
            console.error(JSON.stringify({ success: false, error: 'Missing PID argument' }));
            process.exit(1);
        }
        try {
            const resource = await readResource({ pid });
            console.log(JSON.stringify({ success: true, resource }));
        }
        catch (err) {
            console.error(JSON.stringify({ success: false, error: err.message }));
            process.exit(1);
        }
    }
    main();
}
//# sourceMappingURL=readResource.js.map
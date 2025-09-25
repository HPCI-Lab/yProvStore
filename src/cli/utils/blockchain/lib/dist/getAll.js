"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getResourcesByInterval = void 0;
// createResource.ts
const gatewayHelper_1 = require("./gatewayHelper");
const util_1 = require("util");
const utf8Decoder = new util_1.TextDecoder();
async function getResourcesByInterval(params) {
    const { startTime, endTime } = params;
    if (!startTime || !endTime) {
        throw new Error('Missing required parameters');
    }
    const { contract, gateway, client } = await (0, gatewayHelper_1.getContract)();
    try {
        const result = await contract.submitAsync('GetResourcesByTimestamp', {
            arguments: [
                startTime,
                endTime
            ]
        });
        const status = await result.getStatus();
        if (!status.successful) {
            throw new Error(`Transaction ${status.transactionId} failed with status code ${status.code}`);
        }
        const resource = utf8Decoder.decode(result.getResult());
        return resource;
    }
    finally {
        gateway.close();
        client.close();
    }
}
exports.getResourcesByInterval = getResourcesByInterval;
// Only run main() when file is executed directly (not imported)
if (require.main === module) {
    async function main() {
        const startTime = process.argv[2];
        const endTime = process.argv[3];
        if (!startTime || !endTime) {
            console.error("Missing required arguments.");
            process.exit(1);
        }
        try {
            const resource = await getResourcesByInterval({ startTime, endTime });
            console.log(JSON.stringify({ success: true, resource: resource }));
        }
        catch (err) {
            console.error(JSON.stringify({ success: false, error: err.message }));
            process.exit(1);
        }
    }
    main();
}
//# sourceMappingURL=getAll.js.map
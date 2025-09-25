"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getContract = void 0;
const fabric_gateway_1 = require("@hyperledger/fabric-gateway");
const connect_1 = require("./connect");
const channel_name = 'mychannel';
const chaincode_name = 'cc-test';
async function getContract() {
    const client = await (0, connect_1.newGrpcConnection)();
    const gateway = await (0, fabric_gateway_1.connect)({
        client,
        identity: await (0, connect_1.newIdentity)(),
        signer: await (0, connect_1.newSigner)(),
        hash: fabric_gateway_1.hash.sha256,
        evaluateOptions: () => ({ deadline: Date.now() + 5000 }),
        endorseOptions: () => ({ deadline: Date.now() + 15000 }),
        submitOptions: () => ({ deadline: Date.now() + 5000 }),
        commitStatusOptions: () => ({ deadline: Date.now() + 60000 }),
    });
    const network = gateway.getNetwork(channel_name);
    const contract = network.getContract(chaincode_name);
    return { contract, gateway, client };
}
exports.getContract = getContract;
//# sourceMappingURL=gatewayHelper.js.map
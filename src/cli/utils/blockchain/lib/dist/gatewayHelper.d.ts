import * as grpc from '@grpc/grpc-js';
import { Contract, Gateway } from '@hyperledger/fabric-gateway';
export declare function getContract(): Promise<{
    contract: Contract;
    gateway: Gateway;
    client: grpc.Client;
}>;
//# sourceMappingURL=gatewayHelper.d.ts.map
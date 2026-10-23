`timescale 1ns/1ps
`default_nettype none

module tb;

    reg           clk;
    reg           reset_n;
    reg           encdec;
    reg           init;
    reg           next;
    reg [255:0]   key;
    reg           keylen;
    reg [127:0]   block;

    wire          ready;
    wire [127:0]  result;
    wire          result_valid;

    aes_core dut (
        .clk(clk),
        .reset_n(reset_n),
        .encdec(encdec),
        .init(init),
        .next(next),
        .ready(ready),
        .key(key),
        .keylen(keylen),
        .block(block),
        .result(result),
        .result_valid(result_valid)
    );

    initial begin
        clk = 1'b0;
    end

    always #5 clk = ~clk;

    task wait_ready;
        integer timeout;
        begin
            timeout = 0;

            while ((ready !== 1'b1) && (timeout < 1000)) begin
                @(posedge clk);
                timeout = timeout + 1;
            end

            if (ready !== 1'b1) begin
                $fatal(1, "ERRO: Timeout esperando ready.");
            end
        end
    endtask

    task init_key;
        input [255:0] test_key;
        input         test_keylen;
        integer       timeout;
        begin
            @(negedge clk);

            key    = test_key;
            keylen = test_keylen;
            init   = 1'b1;
            next   = 1'b0;

            @(negedge clk);

            init = 1'b0;

            timeout = 0;

            while ((ready !== 1'b1) && (timeout < 1000)) begin
                @(posedge clk);
                timeout = timeout + 1;
            end

            if (ready !== 1'b1) begin
                $fatal(1, "ERRO: Timeout durante inicializacao da chave.");
            end
        end
    endtask

    task execute_block;
        input         operation;
        input [127:0] input_block;
        input [127:0] expected_result;
        integer       timeout;
        begin
            wait_ready;

            @(negedge clk);

            encdec = operation;
            block  = input_block;
            next   = 1'b1;

            @(negedge clk);

            next = 1'b0;

            timeout = 0;

            while ((result_valid !== 1'b1) && (timeout < 1000)) begin
                @(posedge clk);
                timeout = timeout + 1;
            end

            if (result_valid !== 1'b1) begin
                $fatal(1, "ERRO: Timeout esperando result_valid.");
            end

            #1;

            if (result !== expected_result) begin
                $fatal(1, "ERRO: Resultado=%032h Esperado=%032h", result, expected_result);
            end

            if (operation == 1'b1) begin
                $display("PASSOU: Criptografia correta. Resultado=%032h", result);
            end
            else begin
                $display("PASSOU: Descriptografia correta. Resultado=%032h", result);
            end

            @(posedge clk);
        end
    endtask

    initial begin

        reset_n = 1'b0;
        encdec  = 1'b0;
        init    = 1'b0;
        next    = 1'b0;
        key     = 256'b0;
        keylen  = 1'b0;
        block   = 128'b0;

        repeat (3) @(posedge clk);

        #1;

        if (ready !== 1'b1) begin
            $fatal(1, "ERRO: ready deveria ser 1 durante o reset.");
        end

        if (result_valid !== 1'b0) begin
            $fatal(1, "ERRO: result_valid deveria ser 0 durante o reset.");
        end

        $display("PASSOU: Teste de reset.");

        @(negedge clk);
        reset_n = 1'b1;

        $display("INICIANDO: Teste AES-128.");

        init_key(
            256'h000102030405060708090a0b0c0d0e0f00000000000000000000000000000000,
            1'b0
        );

        $display("PASSOU: Inicializacao da chave AES-128.");

        execute_block(
            1'b1,
            128'h00112233445566778899aabbccddeeff,
            128'h69c4e0d86a7b0430d8cdb78070b4c55a
        );

        execute_block(
            1'b0,
            128'h69c4e0d86a7b0430d8cdb78070b4c55a,
            128'h00112233445566778899aabbccddeeff
        );

        $display("INICIANDO: Teste AES-128 com valores zero.");

        init_key(
            256'h0000000000000000000000000000000000000000000000000000000000000000,
            1'b0
        );

        execute_block(
            1'b1,
            128'h00000000000000000000000000000000,
            128'h66e94bd4ef8a2c3b884cfa59ca342b2e
        );

        execute_block(
            1'b0,
            128'h66e94bd4ef8a2c3b884cfa59ca342b2e,
            128'h00000000000000000000000000000000
        );

        $display("INICIANDO: Teste AES-256.");

        init_key(
            256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f,
            1'b1
        );

        $display("PASSOU: Inicializacao da chave AES-256.");

        execute_block(
            1'b1,
            128'h00112233445566778899aabbccddeeff,
            128'h8ea2b7ca516745bfeafc49904b496089
        );

        execute_block(
            1'b0,
            128'h8ea2b7ca516745bfeafc49904b496089,
            128'h00112233445566778899aabbccddeeff
        );

        $display("TODOS OS TESTES PASSARAM.");

        $finish;
    end

endmodule

`default_nettype wire

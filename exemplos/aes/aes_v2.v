`timescale 1ns/1ps
`default_nettype none
module tb;
    reg         clk;
    reg         reset_n;
    reg         encdec;
    reg         init;
    reg         next;
    reg [255:0] key;
    reg         keylen;
    reg [127:0] block;
    wire         ready;
    wire [127:0] result;
    wire         result_valid;
    integer erros;

    aes_core dut (.clk(clk), .reset_n(reset_n), .encdec(encdec), .init(init),
        .next(next), .ready(ready), .key(key), .keylen(keylen), .block(block),
        .result(result), .result_valid(result_valid));

    initial begin clk = 1'b0; end
    always #5 clk = ~clk;

    task wait_ready;
        integer timeout;
        begin
            timeout = 0;
            while ((ready !== 1'b1) && (timeout < 1000)) begin @(posedge clk); timeout = timeout + 1; end
            if (ready !== 1'b1) $fatal(1, "ERRO: timeout esperando ready.");
        end
    endtask

    task init_key;
        input [255:0] test_key;
        input         test_keylen;
        integer       timeout;
        begin
            wait_ready;
            @(negedge clk); key = test_key; keylen = test_keylen; init = 1'b1; next = 1'b0;
            @(negedge clk); init = 1'b0;
            timeout = 0;
            while ((ready !== 1'b1) && (timeout < 1000)) begin @(posedge clk); timeout = timeout + 1; end
            if (ready !== 1'b1) $fatal(1, "ERRO: timeout durante inicializacao da chave.");
        end
    endtask

    task execute_block;
        input         test_encdec;
        input [127:0] test_block;
        input [127:0] expected_result;
        integer       timeout;
        begin
            wait_ready;
            @(negedge clk); encdec = test_encdec; block = test_block; next = 1'b1;
            @(negedge clk); next = 1'b0;
            timeout = 0;
            while ((result_valid !== 1'b1) && (timeout < 1000)) begin @(posedge clk); timeout = timeout + 1; end
            if (result_valid !== 1'b1) $fatal(1, "ERRO: timeout esperando result_valid.");
            #1;
            if (result !== expected_result) $fatal(1, "ERRO: resultado=%032h esperado=%032h", result, expected_result);
            if (test_encdec === 1'b1) $display("PASSOU: criptografia resultado=%032h", result);
            else $display("PASSOU: descriptografia resultado=%032h", result);
            @(posedge clk);
        end
    endtask

    initial begin
        erros = 0;
        reset_n = 1'b0; encdec = 1'b0; init = 1'b0; next = 1'b0;
        key = 256'b0; keylen = 1'b0; block = 128'b0;
        repeat (3) @(posedge clk); #1;
        if (ready !== 1'b1) $fatal(1, "ERRO: ready deveria ser 1 durante o reset.");
        if (result_valid !== 1'b0) $fatal(1, "ERRO: result_valid deveria ser 0 durante o reset.");
        $display("PASSOU: teste de reset.");
        @(negedge clk); reset_n = 1'b1;

        init_key(256'h000102030405060708090a0b0c0d0e0f00000000000000000000000000000000, 1'b0);
        execute_block(1'b1, 128'h00112233445566778899aabbccddeeff, 128'h69c4e0d86a7b0430d8cdb78070b4c55a);
        execute_block(1'b0, 128'h69c4e0d86a7b0430d8cdb78070b4c55a, 128'h00112233445566778899aabbccddeeff);

        init_key(256'h0000000000000000000000000000000000000000000000000000000000000000, 1'b0);
        execute_block(1'b1, 128'h00000000000000000000000000000000, 128'h66e94bd4ef8a2c3b884cfa59ca342b2e);
        execute_block(1'b0, 128'h66e94bd4ef8a2c3b884cfa59ca342b2e, 128'h00000000000000000000000000000000);

        init_key(256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f, 1'b1);
        execute_block(1'b1, 128'h00112233445566778899aabbccddeeff, 128'h8ea2b7ca516745bfeafc49904b496089);
        execute_block(1'b0, 128'h8ea2b7ca516745bfeafc49904b496089, 128'h00112233445566778899aabbccddeeff);

        if (erros !== 0) $fatal(1, "ERRO: %0d erros encontrados.", erros);
        $display("TODOS OS TESTES PASSARAM.");
        $finish;
    end
endmodule
`default_nettype wire

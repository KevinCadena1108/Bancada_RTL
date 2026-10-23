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
            if (ready !== 1'b1)
                $fatal(1, "ERRO: timeout esperando ready=1.");
        end
    endtask

    task load_key;
        input [255:0] test_key;
        input         test_keylen;
        integer       timeout;
        begin
            wait_ready;
            @(negedge clk);
            key    = test_key;
            keylen = test_keylen;
            init   = 1'b1;
            next   = 1'b0;
            @(negedge clk);
            init = 1'b0;
            if (ready !== 1'b0)
                $fatal(1, "ERRO: ready deveria ficar em 0 durante a inicializacao da chave.");
            timeout = 0;
            while ((ready !== 1'b1) && (timeout < 1000)) begin
                @(posedge clk);
                timeout = timeout + 1;
            end
            if (ready !== 1'b1)
                $fatal(1, "ERRO: timeout durante a expansao da chave.");
            $display("PASSOU: inicializacao da chave.");
        end
    endtask

    task run_block;
        input         test_encdec;
        input [127:0] test_block;
        input [127:0] expected;
        integer       timeout;
        begin
            wait_ready;
            if (result_valid !== 1'b0)
                $fatal(1, "ERRO: result_valid deveria estar em 0 antes de uma nova operacao.");
            @(negedge clk);
            encdec = test_encdec;
            block  = test_block;
            next   = 1'b1;
            @(negedge clk);
            next = 1'b0;
            if (ready !== 1'b0)
                $fatal(1, "ERRO: ready deveria ficar em 0 durante o processamento.");
            timeout = 0;
            while ((result_valid !== 1'b1) && (timeout < 1000)) begin
                @(posedge clk);
                timeout = timeout + 1;
            end
            if (result_valid !== 1'b1)
                $fatal(1, "ERRO: timeout esperando result_valid=1.");
            if (result !== expected)
                $fatal(1, "ERRO: resultado=%032h esperado=%032h.", result, expected);
            if (test_encdec === 1'b1)
                $display("PASSOU: cifracao resultado=%032h.", result);
            else
                $display("PASSOU: decifracao resultado=%032h.", result);
            @(negedge clk);
            if (ready !== 1'b1)
                $fatal(1, "ERRO: ready deveria estar em 1 apos a conclusao.");
        end
    endtask

    initial begin
        reset_n = 1'b0;
        encdec  = 1'b0;
        init    = 1'b0;
        next    = 1'b0;
        key     = 256'h0;
        keylen  = 1'b0;
        block   = 128'h0;

        repeat (3) @(posedge clk);
        if (ready !== 1'b1)
            $fatal(1, "ERRO: ready deveria ser 1 durante o reset.");
        if (result_valid !== 1'b0)
            $fatal(1, "ERRO: result_valid deveria ser 0 durante o reset.");
        $display("PASSOU: reset.");

        @(negedge clk);
        reset_n = 1'b1;
        if (ready !== 1'b1)
            $fatal(1, "ERRO: ready deveria ser 1 apos a liberacao do reset.");

        $display("INICIANDO: AES-128 FIPS 197.");
        load_key(256'h000102030405060708090a0b0c0d0e0f00000000000000000000000000000000, 1'b0);
        run_block(1'b1, 128'h00112233445566778899aabbccddeeff, 128'h69c4e0d86a7b0430d8cdb78070b4c55a);
        run_block(1'b0, 128'h69c4e0d86a7b0430d8cdb78070b4c55a, 128'h00112233445566778899aabbccddeeff);

        $display("INICIANDO: AES-128 vetor zero.");
        load_key(256'h0000000000000000000000000000000000000000000000000000000000000000, 1'b0);
        run_block(1'b1, 128'h00000000000000000000000000000000, 128'h66e94bd4ef8a2c3b884cfa59ca342b2e);
        run_block(1'b0, 128'h66e94bd4ef8a2c3b884cfa59ca342b2e, 128'h00000000000000000000000000000000);

        $display("INICIANDO: AES-256 FIPS 197.");
        load_key(256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f, 1'b1);
        run_block(1'b1, 128'h00112233445566778899aabbccddeeff, 128'h8ea2b7ca516745bfeafc49904b496089);
        run_block(1'b0, 128'h8ea2b7ca516745bfeafc49904b496089, 128'h00112233445566778899aabbccddeeff);

        $display("INICIANDO: AES-256 vetor zero.");
        load_key(256'h0000000000000000000000000000000000000000000000000000000000000000, 1'b1);
        run_block(1'b1, 128'h00000000000000000000000000000000, 128'hdc95c078a2408989ad48a21492842087);
        run_block(1'b0, 128'hdc95c078a2408989ad48a21492842087, 128'h00000000000000000000000000000000);

        $display("TODOS OS TESTES PASSARAM.");
        $finish;
    end

endmodule

`default_nettype wire

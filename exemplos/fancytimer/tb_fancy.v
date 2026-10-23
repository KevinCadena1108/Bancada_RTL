`timescale 1ns/1ps
module tb;
    reg        clk, reset, data, ack;
    wire [3:0] count;
    wire       counting, done;

    integer erros;

    top_module dut (.clk(clk), .reset(reset), .data(data),
                    .count(count), .counting(counting), .done(done), .ack(ack));

    always #5 clk = ~clk;

    // dirige 1 bit por ciclo de clock
    task bit_in(input v);
        begin data = v; @(posedge clk); #1; end
    endtask

    task do_reset;
        begin
            reset = 1'b1; data = 1'b0; ack = 1'b0;
            @(posedge clk); #1;
            reset = 1'b0;
            @(posedge clk); #1;
        end
    endtask

    // envia 1101 + 4 bits de atraso (MSB primeiro) e verifica a temporizacao
    task roda(input [3:0] atraso);
        integer ciclos, esperado;
        begin
            // sequencia de partida 1101
            bit_in(1); bit_in(1); bit_in(0); bit_in(1);
            // 4 bits do atraso, MSB primeiro
            bit_in(atraso[3]); bit_in(atraso[2]); bit_in(atraso[1]); bit_in(atraso[0]);
            data = 1'b0;   // dado nao importa durante a contagem

            // agora deve estar contando, com count == atraso
            if (counting !== 1'b1) begin
                $display("ERRO: nao comecou a contar (atraso=%0d)", atraso);
                erros = erros + 1;
            end
            if (count !== atraso) begin
                $display("ERRO: count inicial=%0d esperado=%0d", count, atraso);
                erros = erros + 1;
            end

            // mede quantos ciclos 'counting' fica alto
            ciclos = 0;
            while (counting === 1'b1) begin
                ciclos = ciclos + 1;
                @(posedge clk); #1;
            end
            esperado = (atraso + 1) * 1000;
            if (ciclos !== esperado) begin
                $display("ERRO: contou %0d ciclos, esperado %0d (atraso=%0d)",
                         ciclos, esperado, atraso);
                erros = erros + 1;
            end

            // ao terminar, done deve subir
            if (done !== 1'b1) begin
                $display("ERRO: done nao subiu ao fim (atraso=%0d)", atraso);
                erros = erros + 1;
            end

            // reconhece (ack) e volta a busca
            ack = 1'b1; @(posedge clk); #1; ack = 1'b0;
            @(posedge clk); #1;
            if (done !== 1'b0) begin
                $display("ERRO: done nao baixou apos ack (atraso=%0d)", atraso);
                erros = erros + 1;
            end
            if (erros == 0)
                $display("OK atraso=%0d: contou %0d ciclos", atraso, ciclos);
        end
    endtask

    initial begin
        clk = 1'b0; erros = 0;
        do_reset;

        roda(4'd0);   // 1000 ciclos
        roda(4'd1);   // 2000 ciclos
        roda(4'd2);   // 3000 ciclos
        roda(4'd4);   // 5000 ciclos

        // reset no meio de uma contagem deve abortar
        bit_in(1); bit_in(1); bit_in(0); bit_in(1);
        bit_in(1); bit_in(1); bit_in(1); bit_in(1);  // atraso=15, contagem longa
        repeat (50) @(posedge clk);
        if (counting !== 1'b1) begin
            $display("ERRO: deveria estar contando antes do reset"); erros = erros + 1;
        end
        reset = 1'b1; @(posedge clk); #1; reset = 1'b0;
        if (counting !== 1'b0) begin
            $display("ERRO: reset nao abortou a contagem"); erros = erros + 1;
        end

        if (erros != 0) $fatal(1, "%0d erro(s)", erros);
        $display("TODOS OS TESTES PASSARAM");
        $finish;
    end
endmodule

`timescale 1ns/1ps

module tb;

    reg  clk, reset, data, ack;
    wire [3:0] count;
    wire counting, done;

    integer erros = 0;
    integer i;

    top_module dut (
        .clk(clk), .reset(reset), .data(data),
        .count(count), .counting(counting), .done(done), .ack(ack)
    );

    always #5 clk = ~clk;

    task send_bit(input b);
    begin
        @(negedge clk);
        data = b;
        @(posedge clk);
        #1;
    end
    endtask

    task inicia_timer(input [3:0] delay);
    begin
        send_bit(1);
        send_bit(1);
        send_bit(0);
        send_bit(1);
        send_bit(delay[3]);
        send_bit(delay[2]);
        send_bit(delay[1]);
        send_bit(delay[0]);
    end
    endtask

    task espera_done(input integer limite, input [3:0] delay_usado);
        integer c;
    begin
        c = 0;
        while (!done && c < limite) begin
            @(posedge clk);
            #1;
            c = c + 1;
        end
        if (!done) begin
            erros = erros + 1;
            $display("[ERRO] delay %0d: done nao subiu em %0d ciclos", delay_usado, limite);
        end else begin
            $display("[OK] delay %0d: done subiu apos %0d ciclos", delay_usado, c);
        end
    end
    endtask

    initial begin
        clk = 0; reset = 1; data = 0; ack = 0;
        @(negedge clk);
        @(negedge clk);
        reset = 0;
        @(negedge clk);

        inicia_timer(4'd0);
        #1;
        if (!counting)
            $display("[AVISO] delay 0: counting nao ativou logo apos carga");
        espera_done(2000, 4'd0);
        @(negedge clk); ack = 1;
        @(negedge clk); ack = 0;
        @(negedge clk);
        #1;
        if (done)
            $display("[AVISO] done nao baixou apos ack");

        inicia_timer(4'd1);
        espera_done(4000, 4'd1);
        @(negedge clk); ack = 1;
        @(negedge clk); ack = 0;
        @(negedge clk);

        inicia_timer(4'd2);
        espera_done(6000, 4'd2);
        @(negedge clk); ack = 1;
        @(negedge clk); ack = 0;
        @(negedge clk);

        if (erros == 0)
            $display("[PASSOU] timer disparou e completou em todos os casos");
        else
            $display("[FALHOU] %0d erros", erros);

        if (erros != 0) $fatal(1, "verificacao encontrou erros");
        $finish;
    end

endmodule

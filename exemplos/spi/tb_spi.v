`timescale 1ns/1ps

module tb;

    reg        rstb;
    reg        clk;
    reg        mlb;
    reg        start;
    reg [7:0]  tdat;
    reg [1:0]  cdiv;
    reg        din;

    wire       ss;
    wire       sck;
    wire       dout;
    wire       done;
    wire [7:0] rdata;

    integer erros;
    integer i;

    spi_master dut (
        .rstb  (rstb),
        .clk   (clk),
        .mlb   (mlb),
        .start (start),
        .tdat  (tdat),
        .cdiv  (cdiv),
        .din   (din),
        .ss    (ss),
        .sck   (sck),
        .dout  (dout),
        .done  (done),
        .rdata (rdata)
    );

    always #5 clk = ~clk;

    task automatic transacao;
        input       modo_mlb;
        input [7:0] tx_data;
        input [7:0] rx_data;
        input [1:0] divisor;
        begin
            mlb   = modo_mlb;
            tdat  = tx_data;
            cdiv  = divisor;

            if (modo_mlb == 1'b0)
                din = rx_data[0];
            else
                din = rx_data[7];

            start = 1'b1;
            @(negedge clk);
            #1;
            start = 1'b0;

            for (i = 0; i < 8; i = i + 1) begin
                @(negedge sck);
                #1;

                if (modo_mlb == 1'b0) begin
                    if (dout !== tx_data[i])
                        $fatal(1, "SPI: dout incorreto no bit %0d, esperado=%b recebido=%b", i, tx_data[i], dout);
                    din = rx_data[i];
                end
                else begin
                    if (dout !== tx_data[7-i])
                        $fatal(1, "SPI: dout incorreto no bit %0d, esperado=%b recebido=%b", i, tx_data[7-i], dout);
                    din = rx_data[7-i];
                end

                @(posedge sck);
                #1;
            end

            if (done !== 1'b1)
                $fatal(1, "SPI: done incorreto, esperado=1 recebido=%b", done);

            if (rdata !== rx_data)
                $fatal(1, "SPI: rdata incorreto, esperado=%h recebido=%h", rx_data, rdata);

            @(negedge clk);
            #1;

            if (ss !== 1'b1)
                $fatal(1, "SPI: ss incorreto ao finalizar, esperado=1 recebido=%b", ss);
        end
    endtask

    initial begin
        erros = 0;

        rstb  = 1'b0;
        clk   = 1'b0;
        mlb   = 1'b0;
        start = 1'b0;
        tdat  = 8'h00;
        cdiv  = 2'b00;
        din   = 1'b0;

        repeat (3) @(negedge clk);
        rstb = 1'b1;

        transacao(1'b0, 8'h3C, 8'hA6, 2'b00);
        $display("[PASSOU] SPI LSB-first ok");

        transacao(1'b1, 8'h96, 8'h5A, 2'b01);
        $display("[PASSOU] SPI MSB-first ok");

        if (erros != 0)
            $fatal(1, "SPI: %0d erros", erros);

        $display("[PASSOU] spi_master ok");
        $finish;
    end

endmodule

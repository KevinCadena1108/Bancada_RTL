module tb;
    reg clk = 0;
    reg load;
    reg [255:0] data;
    wire [255:0] q;
    integer erros = 0;

    top_module dut (.clk(clk), .load(load), .data(data), .q(q));

    always #5 clk = ~clk;
    task step; begin @(posedge clk); #1; end endtask

    initial begin
        load = 1; data = 256'd0; step;
        if (q !== 256'd0) erros = erros + 1;

        load = 1; data = 256'd1; step;
        if (q !== 256'd1) erros = erros + 1;

        load = 0; step;
        if (q !== 256'd0) erros = erros + 1;

        // Bloco 2x2 estavel.
        load = 1;
        data = (256'd1 << 0) | (256'd1 << 1) | (256'd1 << 16) | (256'd1 << 17);
        step;
        if (q !== data) erros = erros + 1;
        load = 0; step;
        if (q !== data) erros = erros + 1;

        // Blinker horizontal (i=1,2,3 ; j=1).
        load = 1;
        data = (256'd1 << 17) | (256'd1 << 18) | (256'd1 << 19);
        step;
        if (q !== data) erros = erros + 1;

        // CORRIGIDO: blinker gira em torno do centro (i=2,j=1) -> vertical i=2, j=0,1,2
        // bits 2 (2+0*16), 18 (2+1*16), 34 (2+2*16).
        load = 0; step;
        if (q !== ((256'd1 << 2) | (256'd1 << 18) | (256'd1 << 34)))
            erros = erros + 1;

        step;
        if (q !== data) erros = erros + 1;

        if (erros != 0) $fatal(1, "game_of_life: %0d erros", erros);
        $display("[PASSOU] Conway's Game of Life 16x16 ok");
        $finish;
    end
endmodule

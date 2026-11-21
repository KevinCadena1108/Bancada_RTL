`default_nettype        none
`define        TXUL_BIT_ZERO        4'h0
`define        TXUL_BIT_ONE        4'h1
`define        TXUL_BIT_TWO        4'h2
`define        TXUL_BIT_THREE        4'h3
`define        TXUL_BIT_FOUR        4'h4
`define        TXUL_BIT_FIVE        4'h5
`define        TXUL_BIT_SIX        4'h6
`define        TXUL_BIT_SEVEN        4'h7
`define        TXUL_STOP        4'h8
`define        TXUL_IDLE        4'hf


module txuartlite(i_clk, i_wr, i_data, o_uart_tx, o_busy);
        parameter        [4:0]        TIMING_BITS = 5'd24;
        localparam                TB = TIMING_BITS;
        parameter        [(TB-1):0]        CLOCKS_PER_BAUD = 8;
        input        wire                i_clk;
        input        wire                i_wr;
        input        wire        [7:0]        i_data;
        output        reg                o_uart_tx;
        output        wire                o_busy;


        reg        [(TB-1):0]        baud_counter;
        reg        [3:0]        state;
        reg        [7:0]        lcl_data;
        reg                r_busy, zero_baud_counter;


        initial        r_busy = 1'b1;
        initial        state  = `TXUL_IDLE;
        always @(posedge i_clk)
        begin
                if (!zero_baud_counter)
                        r_busy <= 1'b1;
                else if (state > `TXUL_STOP)
                begin
                        state <= `TXUL_IDLE;
                        r_busy <= 1'b0;
                        if ((i_wr)&&(!r_busy))
                        begin
                                r_busy <= 1'b1;
                                state <= `TXUL_BIT_ZERO;
                        end
                end else begin
                        r_busy <= 1'b1;
                        if (state <=`TXUL_STOP)
                                state <= state + 1'b1;
                        else
                                state <= `TXUL_IDLE;
                end
        end


        assign        o_busy = (r_busy);


        initial        lcl_data = 8'hff;
        always @(posedge i_clk)
                if ((i_wr)&&(!r_busy))
                        lcl_data <= i_data;
                else if (zero_baud_counter)
                        lcl_data <= { 1'b1, lcl_data[7:1] };


        initial        o_uart_tx = 1'b1;
        always @(posedge i_clk)
                if ((i_wr)&&(!r_busy))
                        o_uart_tx <= 1'b0;
                else if (zero_baud_counter)
                        o_uart_tx <= lcl_data[0];


        initial        zero_baud_counter = 1'b1;
        initial        baud_counter = 0;
        always @(posedge i_clk)
        begin
                zero_baud_counter <= (baud_counter == 1);
                if (state == `TXUL_IDLE)
                begin
                        baud_counter <= 0;
                        zero_baud_counter <= 1'b1;
                        if ((i_wr)&&(!r_busy))
                        begin
                                baud_counter <= CLOCKS_PER_BAUD - 1'b1;
                                zero_baud_counter <= 1'b0;
                        end
                end else if ((zero_baud_counter)&&(state == 4'h9))
                begin
                        baud_counter <= 0;
                        zero_baud_counter <= 1'b1;
                end else if (!zero_baud_counter)
                        baud_counter <= baud_counter - 1'b1;
                else
                        baud_counter <= CLOCKS_PER_BAUD - 1'b1;
        end


endmodule
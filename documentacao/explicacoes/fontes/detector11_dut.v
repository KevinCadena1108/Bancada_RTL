module top_module (
    input clk,
    input rst,
    input in,
    output out
);
    localparam S0 = 2'd0, S1 = 2'd1, S2 = 2'd2;
    reg [1:0] state;

    assign out = (state == S2);

    always @(posedge clk) begin
        if (rst)
            state <= S0;
        else begin
            case (state)
                S0: if (in) state <= S1; else state <= S0;
                S1: if (in) state <= S2; else state <= S0;
                S2: if (in) state <= S2; else state <= S0;
                default: state <= S0;
            endcase
        end
    end
endmodule

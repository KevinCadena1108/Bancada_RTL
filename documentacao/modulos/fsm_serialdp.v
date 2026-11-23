module top_module(
    input clk,
    input in,
    input reset,
    output [7:0] out_byte,
    output reg done
);

    parameter WAIT   = 5'b00001;
    parameter DATA   = 5'b00010;
    parameter CHECK  = 5'b00100;
    parameter PAR_CK = 5'b01000;
    parameter ERR    = 5'b10000;

    reg [4:0] curr_state;
    reg [4:0] next_state;

    wire data_to_parcheck;
    wire par_ok;
    wire check2wait;

    always @(*) begin
        case (curr_state)

            WAIT:
                next_state = (~in) ? DATA : WAIT;

            DATA:
                next_state = (data_to_parcheck) ? PAR_CK : DATA;

            PAR_CK:
                next_state = (par_ok) ? CHECK : ERR;

            CHECK:
                next_state = (in) ? WAIT : ERR;

            ERR:
                next_state = (in) ? WAIT : ERR;

            default:
                next_state = WAIT;

        endcase
    end

    always @(posedge clk) begin
        if (reset)
            curr_state <= WAIT;
        else
            curr_state <= next_state;
    end

    reg [2:0] cnt;

    assign data_to_parcheck =
        (curr_state == DATA) && (cnt == 3'd7);

    always @(posedge clk) begin
        if (reset) begin
            cnt <= 3'd0;
        end
        else if (data_to_parcheck) begin
            cnt <= 3'd0;
        end
        else if (curr_state == DATA) begin
            cnt <= cnt + 3'd1;
        end
    end

    assign check2wait =
        (curr_state == CHECK) && in;

    always @(posedge clk) begin
        if (reset) begin
            done <= 1'b0;
        end
        else if (done) begin
            done <= 1'b0;
        end
        else if (check2wait) begin
            done <= 1'b1;
        end
    end

    reg [7:0] shift_reg;

    always @(posedge clk) begin
        if (reset) begin
            shift_reg <= 8'b0;
        end
        else if ((curr_state == WAIT) && (~in)) begin
            shift_reg <= 8'b0;
        end
        else if (curr_state == DATA) begin
            shift_reg <= {in, shift_reg[7:1]};
        end
    end

    assign par_ok =
        (curr_state == PAR_CK) &&
        (^{in, shift_reg[7:0]});

    assign out_byte = shift_reg;

endmodule
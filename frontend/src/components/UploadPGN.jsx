import { useState } from "react";
import axios from "axios";

function UploadPGN(){
    const [pgn, setPgn] = useState("");
    const analyzeGame = async () => {
    try {

        console.log("Sending request...");

        const response = await axios.post(
            "http://127.0.0.1:5000/analyze",
            {
                pgn: pgn
            }
        );

        console.log("Response received:");
        console.log(response);

        console.log("Response data:");
        console.log(response.data);

    } catch (error) {

        console.error("ERROR:");
        console.error(error);

    }
}
    return(
        <div>
            <h2>Upload Chess PGN</h2>
            <textarea
                placeholder="Paste your PGN here"
                value={pgn}
                onChange={(e)=>{
                    setPgn(e.target.value);
                }}
            />
            <br />
            <button
                onClick={analyzeGame}
            >
                Analyze Game
            </button>
        </div>
    );
}


export default UploadPGN;
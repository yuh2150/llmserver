import time
import logging
from flask import Flask, request, jsonify
from llama_cpp import Llama
import queue
import threading
import json
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
llm = Llama(
    model_path="models/qwen2.5-0.5b-instruct-tuningv1-q4_k_m.gguf",
    # flash_attn=True,
    # chat_format="chatml",
)
request_queue = queue.Queue()
response_dict = {}
def worker():
    while True:
        request_id, messages = request_queue.get()
        try:
            logger.info(f"Processing request ID: {request_id}")
            print(messages)
            for message in messages:
                
                result = llm.create_chat_completion(
                    messages=[
                        { "role": "system",
                            "content": """
You are tasked with extracting specific elements from the provided booking information and returning them as a JSON object. Follow these instructions
Determine whether the following sentence is relevant to the booking address. Irrelevant sentences such as greeting, farewell, phone number, person name, or request, return "null" for all fields
Identify the following fields in the booking information:
from (pickup location)
to (destination)
Extraction rule:
If a field exists, extract its value.
If no field exists, set its value to null.
Make sure that the from and to values ​​are distinct and both exist in the text.
In case of ambiguity:
If referring to only one address, without a specific role, set all fields to null
Construct the extracted values ​​in the following format:
{
"from": "value or null",
"to": "value or null",
}

"""
                            },
                        {"role": "user", "content": message},
                    ],
                    response_format={
                        "type": "json_object",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string", "nullable": True},
                                "to": {"type": "string", "nullable": True},
                            },"required": ["from", "to"],
                        },
                    },
                    temperature=0.8,
                    top_k=90,
                    top_p=0.8
                )
                print(result)
                response_data= result.get("choices", [{}])[0].get("message", {}).get("content", {})
                response_data = str(response_data)
                response_data = json.loads(response_data)
                response_content = {
                    "pickup_location": response_data.get("from"),
                    "destination_location": response_data.get("to"),
                }
                response_dict[request_id] = {"status": "done", "response": response_content}
        except Exception as e:
            logger.error(f"Error during inference for request ID {request_id}: {e}")
            response_dict[request_id] = {"status": "error", "response": str(e)}
        finally:
            request_queue.task_done()

threading.Thread(target=worker, daemon=True).start()

@app.route('/chat', methods=['POST'])
def chat():
    input_data = request.json
    request_id = str(time.time())
    if not input_data or 'messages' not in input_data:
        return jsonify({'error': 'Invalid input'}), 400
    messages = input_data.get('messages', [])
    if not messages or not isinstance(messages, list):
        return jsonify({'error': 'Invalid input, messages must be a non-empty list'}), 400
    request_queue.put((request_id, messages))
    queue_contents = list(request_queue.queue)  # This gets the items in the queue
    print({"queue_contents": queue_contents}), 
    list_responses = []
    for message in messages:   
        # request_queue.put((request_id, message))
        response_dict[request_id] = {"status": "pending", "response": None}
        # Wait for the worker to process the message
        while response_dict[request_id]["status"] == "pending":
            time.sleep(0.0001)

        if response_dict[request_id]["status"] == "done":
            list_responses.append(response_dict[request_id]["response"])
        else:
            list_responses.append({"error": response_dict[request_id]["response"]})
    response = {
        'responses': list_responses
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6006, threaded=True,debug=True)

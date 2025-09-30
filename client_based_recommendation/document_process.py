"""INTERNAL"""
##################### process the document through the rag pipeline #####################
from cognium_codebase.main import main as ragmain
import asyncio
 
user_input = input("Ask away you question, if you have none write quit:\n")  
rag_output = asyncio.run(ragmain(user_input, file_path="/Users/kumnegermatewos/Desktop/Cognium/Codebase/RagAgent/working/client_based_recommendation/output.pdf"))
print(rag_output)

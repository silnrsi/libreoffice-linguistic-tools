/*************************************************************************
 *
 *  $RCSfile: BookmarkInsertion.java,v $
 *
 *  $Revision: 1.5 $
 *
 *  last change: $Author: rt $ $Date: 2005/01/31 17:16:38 $
 *
 *  The Contents of this file are made available subject to the terms of
 *  the BSD license.
 *  
 *  Copyright (c) 2003 by Sun Microsystems, Inc.
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *  1. Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *  2. Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *  3. Neither the name of Sun Microsystems, Inc. nor the names of its
 *     contributors may be used to endorse or promote products derived
 *     from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 *  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 *  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
 *  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 *  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
 *  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
 *  USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *     
 *************************************************************************/

//***************************************************************************
// comment: Step 1: get the Desktop object from the office
//          Step 2: open an empty text document
//          Step 3: enter a example text
//          Step 4: insert some bookmarks
//          
//          Chapter 5.1.1.4 Inserting bookmarks
//***************************************************************************

package org.openoffice.sdk.example.text;

import com.sun.star.awt.Point;
import com.sun.star.awt.Size;
import com.sun.star.beans.PropertyValue;
import com.sun.star.beans.XPropertySet;
import com.sun.star.container.XIndexAccess;
import com.sun.star.container.XNameAccess;
import com.sun.star.drawing.XDrawPage;
import com.sun.star.drawing.XDrawPagesSupplier;
import com.sun.star.drawing.XShape;
import com.sun.star.frame.XDesktop;
import com.sun.star.frame.XDispatchHelper;
import com.sun.star.frame.XDispatchProvider;
import com.sun.star.frame.XModel;
import com.sun.star.frame.XStorable;
import com.sun.star.lang.XMultiServiceFactory;
import com.sun.star.lang.XSingleServiceFactory;
import com.sun.star.sdb.XDocumentDataSource;
import com.sun.star.text.XText;
import com.sun.star.text.XTextCursor;
import com.sun.star.uno.UnoRuntime;
import com.sun.star.text.XTextDocument;
import com.sun.star.text.XTextRange;
import com.sun.star.uno.XNamingService;
import com.sun.star.view.XPrintJobBroadcaster;
import com.sun.star.view.XPrintJobListener;
//import javax.print.event.PrintJobEvent;
import com.sun.star.view.PrintJobEvent;
//import com.sun.star.container.XNamed;

public class BookmarkInsertion {

	static XDispatchHelper dispatcher = null;

    public static void main(String args[]) {
    //public static void was_main(String args[]) {
	System.out.println("main() BEGIN");
	//printDataSources();
        // You need the desktop to create a document
        // The getDesktop method does the UNO bootstrapping, gets the
        // remote servie manager and the desktop object.
        //com.sun.star.frame.XDesktop xDesktop = null;
        com.sun.star.frame.XDesktop xDesktop = getDesktop();
	//createNewDataSource2();
	//System.exit(0);
       
        // create text document
        XTextDocument xTextDocument = null;
		XText xText = null;
        com.sun.star.lang.XComponent xComponent = null;
        xTextDocument = createTextdocument(xDesktop);
        
          try {
        // open current document
        xComponent = xDesktop.getCurrentComponent();
        //xTextDocument =(XTextDocument)UnoRuntime.queryInterface(XTextDocument.class, xComponent);
        //xText = (XText)UnoRuntime.queryInterface(XText.class, xComponent);
        //xText = (XText)UnoRuntime.queryInterface(XText.class, xComponent);
        //xText = (XText)UnoRuntime.queryInterface(XText.class, xTextDocument);
		xText = xTextDocument.getText();
		XTextRange xTextRange = xText.getStart();
		XTextCursor xTextCursor = xText.createTextCursorByRange(xTextRange);
		//XTextCursor xTextCursor = xText.createTextCursorByRange(xText.getStart());
		//XTextCursor xTextCursor = xText.createTextCursorByRange(xText.getStart());
		//XTextCursor xTextCursor = xTextDocument.getText().createTextCursorByRange(xText.getStart());
		//xTextCursor.collapseToStart();
		int num_chars = 0;
        while (xTextCursor.goRight((short)1, false)) { num_chars++; }
		System.out.println("Found " + num_chars + " characters.");

        /*
		XDrawPagesSupplier xDrawPagesSupplier = 
			(XDrawPagesSupplier)UnoRuntime.queryInterface(
				XDrawPagesSupplier.class, xComponent);
		Object drawPages = xDrawPagesSupplier.getDrawPages();
		XIndexAccess xIndexedDrawPages = (XIndexAccess)UnoRuntime.queryInterface(
			XIndexAccess.class, drawPages);
		Object drawPage = xIndexedDrawPages.getByIndex(0);
		XMultiServiceFactory xDrawFactory = 
                  (XMultiServiceFactory)UnoRuntime.queryInterface(
                      XMultiServiceFactory.class, xComponent);
		Object drawShape = xDrawFactory.createInstance("com.sun.star.drawing.RectangleShape");
		XDrawPage xDrawPage = (XDrawPage)UnoRuntime.queryInterface(XDrawPage.class, drawPage);
		XShape xDrawShape = UnoRuntime.queryInterface(XShape.class, drawShape);
		xDrawShape.setSize(new Size(10000, 20000));
		xDrawShape.setPosition(new Point(5000, 5000));
		xDrawPage.add(xDrawShape);

		XText xShapeText = UnoRuntime.queryInterface(XText.class, drawShape);
		XPropertySet xShapeProps = UnoRuntime.queryInterface(XPropertySet.class, drawShape);
		xShapeText.setString("DEF");

		System.exit(0);
        */

                /*
                    com.sun.star.frame.XComponentLoader xCompLoader =
                (com.sun.star.frame.XComponentLoader)
                     UnoRuntime.queryInterface(
                         com.sun.star.frame.XComponentLoader.class, xDesktop);

            String sUrl = "c:/users/jimstandard/desktop/formdata/form2.odt";
            //if ( sUrl.indexOf("private:") != 0) {
                java.io.File sourceFile = new java.io.File(sUrl);
                StringBuffer sbTmp = new StringBuffer("file:///");
                sbTmp.append(sourceFile.getCanonicalPath().replace('\\', '/'));
                sUrl = sbTmp.toString();
            //}    
      
            // Load a Writer document, which will be automaticly displayed
            com.sun.star.lang.XComponent xComponent = xCompLoader.loadComponentFromURL(
                sUrl, "_blank", 0, new com.sun.star.beans.PropertyValue[0]);
        */
        } catch( Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }


          /*
	  	PropertyValue[] printProperties = new PropertyValue[1];
		printProperties[0] = new PropertyValue();
		printProperties[0].Name = "Print";
		printProperties[0].Value = new Boolean(true);

		XDispatchProvider xDispatchProvider = (XDispatchProvider)
			UnoRuntime.queryInterface (XDispatchProvider.class, xDesktop);

	XPrintJobBroadcaster xPrintJobBroadcaster = (XPrintJobBroadcaster)
		UnoRuntime.queryInterface(XPrintJobBroadcaster.class, xComponent);  
	xPrintJobBroadcaster.addPrintJobListener(new MyPrintJobListener());

	com.sun.star.view.XPrintable xPrintable =
		(com.sun.star.view.XPrintable)UnoRuntime.queryInterface(
			com.sun.star.view.XPrintable.class, xComponent);
	xPrintable.print(printProperties);
          */

		//dispatcher.executeDispatch(
		//	xDispatchProvider, ".uno:Print","_self", 0, printProperties);

		//try { Thread.sleep(10000); } catch (Exception e) {}
		  /*
		try {
			XBookmarksSupplier xBookmarksSupplier =
				(XBookmarksSupplier)UnoRuntime.queryInterface(
				XBookmarksSupplier.class, xComponent);
				XNameAccess xNamedBookmarks = xBookmarksSupplier.getBookmarks();
			Object bookmark = xNamedBookmarks.getByName("TextAndTable");
			XTextContent xBookmarkContent = (XTextContent)UnoRuntime.queryInterface(
				XTextContent.class, bookmark);
			XTextRange xTextRange = xBookmarkContent.getAnchor();
            //XTextCursor xTextCursor = (XTextCursor)
            //    xTextDocument.getText().createTextCursorByRange(xTextRange);
            //TextRange textRange = (TextRange)UnoRuntime.queryInterface(
            //    TextRange.class, xTextRange);
            XContentEnumerationAccess xContentEnum = (XContentEnumerationAccess)
                UnoRuntime.queryInterface(
                XContentEnumerationAccess.class, xTextRange);
            XEnumeration xTextTableEnum = (XEnumeration)
               xContentEnum.createContentEnumeration(
               "com::sun::star::text::TextTable");
            //XContentEnumerationAccess xTextTableEnum = (XContentEnumerationAccess)
            //   xTextCursor.createContentEnumeration(
            //   "com::sun::star::text::TextTable");
            while (xTextTableEnum.hasMoreElements()) {
                XServiceInfo xInfo = (XServiceInfo) UnoRuntime.queryInterface(
                    XServiceInfo.class, xTextTableEnum.nextElement());
                if (xInfo.supportsService("com.sun.star.text.TextTable")) {
                    XPropertySet xSet = (XPropertySet) UnoRuntime.queryInterface(
                    XPropertySet.class, xInfo);
                    System.out.println(xSet.getPropertyValue("Name"));
                }
			}
        } catch( Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }
        */

        xText = (XText)xTextDocument.getText();
        XTextRange xTextRange = xText.getEnd();
        xTextRange.setString( "(JavaBegin1)" );
        /*
        XFormsSupplier xFormsSupplier = UnoRuntime.queryInterface(XFormsSupplier.class, xComponent);
        //XNameContainer xforms = xFormsSupplier.getXForms();
        XNameContainer xforms = xFormsSupplier.getXForms();
        String formName = xforms.getElementNames()[0];
        xTextRange = xText.getEnd();
        xTextRange.setString(formName);
        
        Object aForm = xforms.getByName(formName);
        XForms xform = (XForms) UnoRuntime.queryInterface(XForms.class, aForm);
        } catch( Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }
        // put example text in document
        createExampleData(xTextDocument);
        
        
        String mOffending[] = { "negro(e|es)?","bor(ed|ing)?",
                                "bloody?", "bleed(ing)?" };
        String mBad[] = { "possib(le|ilit(y|ies))", "real(ly)+", "brilliant" };
        
        String sOffendPrefix = "Offending";
        String sBadPrefix = "BadStyle";
        
        markList(xTextDocument, mOffending, sOffendPrefix);
        markList(xTextDocument, mBad, sBadPrefix);
        String tblName = "Table1";
        boolean flag = true;
        int size = 5;
        XTextTablesSupplier xTablesSupplier = (XTextTablesSupplier)
                UnoRuntime.queryInterface(XTextTablesSupplier.class, xTextDocument);
        */

    //XNameAccess xNamedTables = xTablesSupplier.getTextTables();
    try {
		/*
		//XPropertySet propSet = UnoRuntime.queryInterface(XPropertySet.class, xTextDocument);
		//propSet.setPropertyValue("HeaderIsOn", Boolean.FALSE);
		//propSet.setPropertyValue("FooterIsOn", Boolean.FALSE);
         XStyleFamiliesSupplier xSupplier = (XStyleFamiliesSupplier)UnoRuntime.queryInterface(
             XStyleFamiliesSupplier.class, xTextDocument);
         XNameAccess xFamilies = (XNameAccess) UnoRuntime.queryInterface ( 
             XNameAccess.class, xSupplier.getStyleFamilies());
         XNameContainer xFamily = (XNameContainer) UnoRuntime.queryInterface( 
             XNameContainer.class, xFamilies.getByName("PageStyles"));
		//XStyle xStyle = (XStyle)xFamily.getByName("Default");
		//XStyle xStyle = (XStyle)xFamily.getByName("Default Style");
		XStyle xStyle = (XStyle) UnoRuntime.queryInterface(XStyle.class, xFamily.getByName("Default Style"));
		XPropertySet xStyleProps = (XPropertySet) UnoRuntime.queryInterface(
        	XPropertySet.class, xStyle);
        xStyleProps.setPropertyValue ("HeaderIsOn", Boolean.FALSE);
        xStyleProps.setPropertyValue ("FooterIsOn", Boolean.FALSE);
        //xStyleProps.setPropertyValue ("HeaderIsOn", Boolean.TRUE);
        //xStyleProps.setPropertyValue ("FooterIsOn", Boolean.TRUE);
		*/

		/*
        Object table = xNamedTables.getByName(tblName);
        //XTextTable xTable = (XTextTable) UnoRuntime.queryInterface(XTextTable.class, table);
        //XCellRange xCellRange = (XCellRange) UnoRuntime.queryInterface(XCellRange.class, table);
            if(flag){
                
                XColumnRowRange xCollumnAndRowRange = (XColumnRowRange) 
                //        UnoRuntime.queryInterface(XColumnRowRange.class, xCellRange);
                                UnoRuntime.queryInterface(XColumnRowRange.class, table);
                XTableRows rows = xCollumnAndRowRange.getRows();
                // 
                //XTableRows rows = xTable.getRows();

                System.out.println("Testing if this works");
                rows.insertByIndex(4, size-4);
            }
		*/
        } catch( Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }
		System.out.println("main() END");
        
        System.exit(0);        
    }
    
    public static void markList(com.sun.star.text.XTextDocument xTextDocument,
                                String mList[], String sPrefix) {
        int iCounter=0;
        com.sun.star.uno.XInterface xSearchInterface = null;
        com.sun.star.text.XTextRange xSearchTextRange = null;
        
        try {
            for( iCounter = 0; iCounter < mList.length; iCounter++ ) {
                // the findfirst returns a XInterface
                xSearchInterface = (com.sun.star.uno.XInterface)FindFirst(
                    xTextDocument, mList[ iCounter ] );
                
                if( xSearchInterface != null ) {
                    // get the TextRange form the XInterface
                    xSearchTextRange = (com.sun.star.text.XTextRange)
                        UnoRuntime.queryInterface(
                            com.sun.star.text.XTextRange.class, xSearchInterface);
                    
                    InsertBookmark(xTextDocument, xSearchTextRange,
                                   sPrefix + iCounter);
                }
            }
        }
        catch( Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }        
    }
    
    
    public static void InsertBookmark(com.sun.star.text.XTextDocument xTextDocument,
                                      com.sun.star.text.XTextRange xTextRange,
                                      String sBookName) {
        // create a bookmark on a TextRange
        try {
            // get the MultiServiceFactory from the text document
            com.sun.star.lang.XMultiServiceFactory xDocMSF;
            xDocMSF = (com.sun.star.lang.XMultiServiceFactory)
                UnoRuntime.queryInterface(
                    com.sun.star.lang.XMultiServiceFactory.class, xTextDocument);
            
            // the bookmark service is a context dependend service, you need
            // the MultiServiceFactory from the document
            Object xObject = xDocMSF.createInstance("com.sun.star.text.Bookmark");
            
            // set the name from the bookmark
            com.sun.star.container.XNamed xNameAccess = null;
            xNameAccess = (com.sun.star.container.XNamed)
                UnoRuntime.queryInterface(
                    com.sun.star.container.XNamed.class, xObject);
            
            xNameAccess.setName(sBookName);
            
            // create a XTextContent, for the method 'insertTextContent'
            com.sun.star.text.XTextContent xTextContent = null;
            xTextContent = (com.sun.star.text.XTextContent)
                UnoRuntime.queryInterface(
                    com.sun.star.text.XTextContent.class, xNameAccess);
            
            // insertTextContent need a TextRange not a cursor to specify the
            // position from the bookmark
            xTextDocument.getText().insertTextContent(xTextRange, xTextContent, true);

            System.out.println("Insert bookmark: " + sBookName);
        }
        catch( Exception e) {
            e.printStackTrace(System.err);
        }
    }
    
    protected static com.sun.star.uno.XInterface FindFirst(
        com.sun.star.text.XTextDocument xTextDocument, String sSearchString)
    {
        com.sun.star.util.XSearchDescriptor xSearchDescriptor = null;
        com.sun.star.util.XSearchable xSearchable = null;
        com.sun.star.uno.XInterface xSearchInterface = null;
        
        try {
            xSearchable = (com.sun.star.util.XSearchable)
                UnoRuntime.queryInterface(
                    com.sun.star.util.XSearchable.class, xTextDocument);
            xSearchDescriptor = (com.sun.star.util.XSearchDescriptor)
                xSearchable.createSearchDescriptor();
            
            xSearchDescriptor.setSearchString(sSearchString);
            
            com.sun.star.beans.XPropertySet xPropertySet = null;
            xPropertySet = (com.sun.star.beans.XPropertySet)
                UnoRuntime.queryInterface(
                    com.sun.star.beans.XPropertySet.class, xSearchDescriptor);
            
            xPropertySet.setPropertyValue("SearchRegularExpression",
                                          new Boolean( true ) );
            
            xSearchInterface = (com.sun.star.uno.XInterface)
                xSearchable.findFirst(xSearchDescriptor);
        }
        catch( Exception e) {
            e.printStackTrace(System.err);
        }
        
        return xSearchInterface;
    }
    
    protected static void createExampleData(
        com.sun.star.text.XTextDocument xTextDocument )
    {
        com.sun.star.text.XTextCursor xTextCursor = null;
        
        try {
            xTextCursor = (com.sun.star.text.XTextCursor)
                xTextDocument.getText().createTextCursor();
            
            xTextCursor.setString( "He heard quiet steps behind him. That didn't bode well. Who could be following him this late at night and in this deadbeat part of town? And at this particular moment, just after he pulled off the big time and was making off with the greenbacks. Was there another crook who'd had the same idea, and was now watching him and waiting for a chance to grab the fruit of his labor?" );
            xTextCursor.collapseToEnd();
            xTextCursor.setString( "Or did the steps behind him mean that one of many bloody officers in town was on to him and just waiting to pounce and snap those cuffs on his wrists? He nervously looked all around. Suddenly he saw the alley. Like lightening he darted off to the left and disappeared between the two warehouses almost falling over the trash can lying in the middle of the sidewalk. He tried to nervously tap his way along in the inky darkness and suddenly stiffened: it was a dead-end, he would have to go back the way he had come" );
            xTextCursor.collapseToEnd();
            xTextCursor.setString( "The steps got louder and louder, he saw the black outline of a figure coming around the corner. Is this the end of the line? he thought pressing himself back against the wall trying to make himself invisible in the dark, was all that planning and energy wasted? He was dripping with sweat now, cold and wet, he could smell the brilliant fear coming off his clothes. Suddenly next to him, with a barely noticeable squeak, a door swung quietly to and fro in the night's breeze." );
            
            xTextCursor.gotoStart(false);
        }
        catch( Exception e) {
            e.printStackTrace(System.err);
        }
        
    } 
    
    public static com.sun.star.frame.XDesktop getDesktop() {
        com.sun.star.frame.XDesktop xDesktop = null;
        com.sun.star.lang.XMultiComponentFactory xMCF = null;
        
        try {
            com.sun.star.uno.XComponentContext xContext = null;
            
            // get the remote office component context
            xContext = com.sun.star.comp.helper.Bootstrap.bootstrap();
            
            // get the remote office service manager
            xMCF = xContext.getServiceManager();
            if( xMCF != null ) {
                System.out.println("Connected to a running office ...");

                Object oDesktop = xMCF.createInstanceWithContext(
                    "com.sun.star.frame.Desktop", xContext);
                xDesktop = (com.sun.star.frame.XDesktop) UnoRuntime.queryInterface(
                    com.sun.star.frame.XDesktop.class, oDesktop);

				XDesktop xd = (XDesktop)UnoRuntime.queryInterface(
					XDesktop.class, oDesktop);
				final Object helper = xMCF.createInstanceWithContext(
					"com.sun.star.frame.DispatchHelper", xContext);
				dispatcher = (XDispatchHelper)UnoRuntime.queryInterface(
					XDispatchHelper.class, helper);
            }
            else
                System.out.println( "Can't create a desktop. No connection, no remote office servicemanager available!" );
        }
        catch( Exception e) {
            e.printStackTrace(System.err);
            System.exit(1);
        }
        
        
        return xDesktop;
    }
    
    public static com.sun.star.text.XTextDocument createTextdocument(
        com.sun.star.frame.XDesktop xDesktop )
    {
        com.sun.star.text.XTextDocument aTextDocument = null;
        
        try {
            com.sun.star.lang.XComponent xComponent = CreateNewDocument(xDesktop,
                                                                        "swriter");
            aTextDocument = (com.sun.star.text.XTextDocument)
                UnoRuntime.queryInterface(
                    com.sun.star.text.XTextDocument.class, xComponent);
        }
        catch( Exception e) {
            e.printStackTrace(System.err);
        }
        
        return aTextDocument;
    }
    
    
    protected static com.sun.star.lang.XComponent CreateNewDocument(
        com.sun.star.frame.XDesktop xDesktop,
        String sDocumentType )
    {
        String sURL = "private:factory/" + sDocumentType;
        
        com.sun.star.lang.XComponent xComponent = null;
        com.sun.star.frame.XComponentLoader xComponentLoader = null;
        com.sun.star.beans.PropertyValue xValues[] =
            new com.sun.star.beans.PropertyValue[1];
        com.sun.star.beans.PropertyValue xEmptyArgs[] =
            new com.sun.star.beans.PropertyValue[0];
        
        try {
            xComponentLoader = (com.sun.star.frame.XComponentLoader)
                UnoRuntime.queryInterface(
                    com.sun.star.frame.XComponentLoader.class, xDesktop);
        
            xComponent  = xComponentLoader.loadComponentFromURL(
                sURL, "_blank", 0, xEmptyArgs);
        }
        catch( Exception e) {
            e.printStackTrace(System.out);
        }
        
        return xComponent ;
    }

    // creates a new DataSource
    public static void createNewDataSource()
    {
        try
        {
            // get the remote office component context
            com.sun.star.uno.XComponentContext xContext = null;
            xContext = com.sun.star.comp.helper.Bootstrap.bootstrap();
            XMultiServiceFactory _rMSF = (XMultiServiceFactory)UnoRuntime.queryInterface(
                XMultiServiceFactory.class,  xContext.getServiceManager());
        
            // the XSingleServiceFactory of the database context creates new generic 
            // com.sun.star.sdb.DataSources (!)
            // retrieve the database context at the global service manager and get its 
            // XSingleServiceFactory interface
            XSingleServiceFactory xFac = (XSingleServiceFactory)UnoRuntime.queryInterface(
                XSingleServiceFactory.class, _rMSF.createInstance("com.sun.star.sdb.DatabaseContext"));

            // instantiate an empty data source at the XSingleServiceFactory 
            // interface of the DatabaseContext
            Object xDs = xFac.createInstance();
            if (xDs != null)
                System.out.println("Created new data source.");

            /*
            // register it with the database context
            XStorable store = (XStorable)UnoRuntime.queryInterface(
                    XStorable.class, xDs);
            XModel model = (XModel)UnoRuntime.queryInterface(
                    XModel.class, xDs);
            */
            XDocumentDataSource datasourceDocument =
                UnoRuntime.queryInterface(XDocumentDataSource.class, xDs);
            XStorable store = (XStorable) UnoRuntime.queryInterface(XStorable.class, datasourceDocument);
            XModel model = UnoRuntime.queryInterface(XModel.class, datasourceDocument);
            //XDocumentDataSource datasource = UnoRuntime.queryInterface(XDocumentDataSource.class, xFac);
            //XStorable store = (XStorable) UnoRuntime.queryInterface(XStorable.class, datasource.getDatabaseDocument());
            //XModel model = UnoRuntime.queryInterface(XModel.class, datasource.getDatabaseDocument());
            if (store == null) {
                System.err.println("Could not get XStorable interface from new data source.");
                System.exit(0);
            }
            store.storeAsURL(
                    "file:///c:/Users/jkkor/Desktop/test.odb",model.getArgs());
            XNamingService xServ = (XNamingService)UnoRuntime.queryInterface(
                    XNamingService.class, xFac);
            xServ.registerObject("NewDataSourceName", xDs);

            // setting the necessary data source properties
            XPropertySet xDsProps = (XPropertySet)UnoRuntime.queryInterface(XPropertySet.class, xDs);
            // Adabas D URL
            xDsProps.setPropertyValue("URL", "jdbc:mysql::MYSQL");

            // force password dialog
            xDsProps.setPropertyValue("IsPasswordRequired", new Boolean(true));

            // suggest dsadmin as user name
            xDsProps.setPropertyValue("User", "root");
            store.store();
        } catch (Exception exc) {
                exc.printStackTrace(System.out);
        }
    }

    // creates a new DataSource
    public static void createNewDataSource2()
    {
        try
        {
            com.sun.star.uno.XComponentContext xContext = null;
            xContext = com.sun.star.comp.helper.Bootstrap.bootstrap();
            XMultiServiceFactory _rMSF = (XMultiServiceFactory)UnoRuntime.queryInterface(
                XMultiServiceFactory.class,  xContext.getServiceManager());
        
            // the XSingleServiceFactory of the database context creates new generic 
            // com.sun.star.sdb.DataSources (!)
            // retrieve the database context at the global service manager and get its 
            // XSingleServiceFactory interface
            XSingleServiceFactory xFac = (XSingleServiceFactory)UnoRuntime.queryInterface(
                XSingleServiceFactory.class, _rMSF.createInstance("com.sun.star.sdb.DatabaseContext"));

            // instantiate an empty data source at the XSingleServiceFactory 
            // interface of the DatabaseContext
            Object xDs = xFac.createInstance();
            if (xDs != null)
                System.out.println("Created new data source.");

            /*
            // register it with the database context
            XStorable store = (XStorable)UnoRuntime.queryInterface(
                    XStorable.class, xDs);
            XModel model = (XModel)UnoRuntime.queryInterface(
                    XModel.class, xDs);
            */
            XDocumentDataSource datasourceDocument =
                UnoRuntime.queryInterface(XDocumentDataSource.class, xDs);
            XStorable store = (XStorable) UnoRuntime.queryInterface(XStorable.class, datasourceDocument);
            XModel model = UnoRuntime.queryInterface(XModel.class, datasourceDocument);
            //XDocumentDataSource datasource = UnoRuntime.queryInterface(XDocumentDataSource.class, xFac);
            //XStorable store = (XStorable) UnoRuntime.queryInterface(XStorable.class, datasource.getDatabaseDocument());
            //XModel model = UnoRuntime.queryInterface(XModel.class, datasource.getDatabaseDocument());
            if (store == null) {
                System.err.println("Could not get XStorable interface from new data source.");
                System.exit(0);
            }
            store.storeAsURL(
                    "file:///c:/Users/jkkor/Desktop/test.odb",model.getArgs());
            XNamingService xServ = (XNamingService)UnoRuntime.queryInterface(
                    XNamingService.class, xFac);
            xServ.registerObject("NewDataSourceName", xDs);

            // setting the necessary data source properties
            XPropertySet xDsProps = (XPropertySet)UnoRuntime.queryInterface(XPropertySet.class, xDs);
            // Adabas D URL
            xDsProps.setPropertyValue("URL", "jdbc:mysql::MYSQL");

            // force password dialog
            xDsProps.setPropertyValue("IsPasswordRequired", new Boolean(true));

            // suggest dsadmin as user name
            xDsProps.setPropertyValue("User", "root");
            store.store();
        } catch (Exception exc) {
                exc.printStackTrace(System.out);
        }
    }

    // prints all data sources
    public static void printDataSources()
    {
        System.out.println("Data Sources:");
        try
        {
            // get the remote office component context
            com.sun.star.uno.XComponentContext xContext = null;
            xContext = com.sun.star.comp.helper.Bootstrap.bootstrap();
            XMultiServiceFactory _rMSF = (XMultiServiceFactory)UnoRuntime.queryInterface(
                XMultiServiceFactory.class,  xContext.getServiceManager());

            // retrieve the DatabaseContext and get its com.sun.star.container.XNameAccess interface
            XNameAccess xNameAccess = (XNameAccess)UnoRuntime.queryInterface(
                XNameAccess.class, _rMSF.createInstance("com.sun.star.sdb.DatabaseContext"));
     
             // print all DataSource names
             String aNames [] = xNameAccess.getElementNames();
             for (int i=0;i<aNames.length;++i)
                System.out.println("  " + aNames[i]);
        } catch (Exception exc) {
                exc.printStackTrace(System.out);
        }
        System.out.println("End Data Sources.");
    }
}

	class MyPrintJobListener implements XPrintJobListener {
		public void printJobEvent(PrintJobEvent printJobEvent) {
			//AppletLogger.log("printing");
			System.out.println("print status: " + printJobEvent.State.getValue());
		}
		public void disposing(com.sun.star.lang.EventObject eventObject) {
			System.out.println("disposing");
		}
	}
